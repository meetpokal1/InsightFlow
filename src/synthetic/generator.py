"""Generate a clean, internally consistent synthetic dataset.

Dirt is added afterwards by corrupt.py, so the clean data can be used as ground truth.
Everything is driven by one seeded random generator, so the same seed gives the same data.
"""

import logging
import math
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.synthetic import catalog

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SyntheticConfig:
    seed: int = 42
    n_customers: int = 800
    start: date = catalog.DATA_START
    end: date = catalog.DATA_END
    snapshot_date: date = catalog.INVENTORY_SNAPSHOT_DATE


@dataclass
class CleanDataset:
    categories: pd.DataFrame
    suppliers: pd.DataFrame
    locations: pd.DataFrame
    products: pd.DataFrame
    customers: pd.DataFrame
    orders: pd.DataFrame
    order_items: pd.DataFrame
    inventory: pd.DataFrame

    def tables(self):
        return {
            "categories": self.categories,
            "suppliers": self.suppliers,
            "locations": self.locations,
            "products": self.products,
            "customers": self.customers,
            "orders": self.orders,
            "order_items": self.order_items,
            "inventory": self.inventory,
        }


def build_categories():
    rows = [
        {"category_id": cid, "category_name": name} for cid, (name, _) in catalog.CATEGORIES.items()
    ]
    return pd.DataFrame(rows)


def build_suppliers():
    rows = []
    for supplier_id, (name, city, lead_time, _) in catalog.SUPPLIERS.items():
        domain = "".join(ch for ch in "".join(name.lower().split()[:2]) if ch.isalnum())
        rows.append(
            {
                "supplier_id": supplier_id,
                "supplier_name": name,
                "city": city,
                "contact_email": f"sales@{domain}.example",
                "lead_time_days": lead_time,
            }
        )
    return pd.DataFrame(rows)


def build_locations():
    rows = []
    for location_id, (city, state, region, location_type, _) in catalog.LOCATIONS.items():
        rows.append(
            {
                "location_id": location_id,
                "location_name": f"{city} {location_type}",
                "city": city,
                "state": state,
                "region": region,
                "location_type": location_type,
            }
        )
    return pd.DataFrame(rows)


def build_products(rng):
    """Products plus a popularity column that only the generator uses (dropped later)."""
    rows = []
    number = 0
    for category_id, templates in catalog.PRODUCT_TEMPLATES.items():
        suppliers = [sid for sid, s in catalog.SUPPLIERS.items() if category_id in s[3]]
        for name, unit, price, margin, popularity in templates:
            number += 1
            rows.append(
                {
                    "product_id": f"P{number:04d}",
                    "product_name": name,
                    "category_id": category_id,
                    "supplier_id": str(rng.choice(suppliers)),
                    "cost_price": round(price * (1 - margin), 2),
                    "selling_price": float(price),
                    "unit": unit,
                    "popularity": popularity,
                }
            )
    return pd.DataFrame(rows)


def build_customers(rng, config):
    types = list(catalog.CUSTOMER_TYPE_MIX)
    type_probs = list(catalog.CUSTOMER_TYPE_MIX.values())
    cities = [city for city, *_ in catalog.LOCATIONS.values()]
    city_probs = np.array([share for *_, share in catalog.LOCATIONS.values()])
    city_probs = city_probs / city_probs.sum()

    window_days = (config.end - config.start).days
    old_start = date(2022, 1, 1)
    rows = []
    for i in range(config.n_customers):
        customer_type = str(rng.choice(types, p=type_probs))
        if rng.random() < 0.55:
            # existing customer, signed up before the data window starts
            signup = old_start + timedelta(
                days=int(rng.integers(0, (config.start - old_start).days))
            )
        else:
            # new customer acquired during the window, a bit more of them early on
            signup = config.start + timedelta(days=int(window_days * rng.beta(1.0, 1.4) * 0.97))

        first = str(rng.choice(catalog.FIRST_NAMES))
        last = str(rng.choice(catalog.LAST_NAMES))
        if customer_type == "Retail":
            name = f"{first} {last}"
            email_name = f"{first}.{last}".lower()
        elif customer_type == "Wholesale":
            trader_word = str(rng.choice(catalog.TRADER_WORDS))
            name = f"{last} {trader_word}"
            email_name = f"{last}.{trader_word.split()[-1]}".lower()
        else:
            name = f"{rng.choice(catalog.COMPANY_WORDS)} {rng.choice(catalog.COMPANY_SUFFIXES)}"
            email_name = f"{name.split()[0]}.procurement".lower()

        rows.append(
            {
                "customer_id": f"C{i + 1:05d}",
                "customer_name": name,
                "email": f"{email_name}{i + 1}@{rng.choice(catalog.EMAIL_DOMAINS)}",
                "phone": f"{rng.choice([6, 7, 8, 9])}{int(rng.integers(0, 10**9)):09d}",
                "city": str(rng.choice(cities, p=city_probs)),
                "customer_type": customer_type,
                "signup_date": signup,
            }
        )
    return pd.DataFrame(rows)


def day_weights(config):
    """Relative chance of an order on each day: seasonality times yearly growth."""
    days = pd.date_range(config.start, config.end, freq="D")
    seasonality = np.array([catalog.MONTH_SEASONALITY[d.month] for d in days])
    growth = (1 + catalog.OVERALL_ANNUAL_GROWTH) ** (np.arange(len(days)) / 365)
    return days, seasonality * growth


def customer_order_dates(rng, customer, activity, days, weights, config):
    first_day = max(customer.signup_date, config.start)
    start_idx = (pd.Timestamp(first_day) - days[0]).days
    active_share = (len(days) - start_idx) / len(days)
    is_new = customer.signup_date >= config.start

    expected = catalog.CUSTOMER_TYPE_MEAN_ORDERS[customer.customer_type] * active_share * activity
    n_orders = int(rng.poisson(expected))
    if is_new:
        n_orders = max(n_orders, 1)  # a new customer is a customer because they ordered

    dates = []
    if is_new:
        first_order_idx = min(start_idx + int(rng.integers(0, 6)), len(days) - 1)
        dates.append(days[first_order_idx])
        n_orders -= 1
    if n_orders > 0:
        remaining = weights[start_idx:]
        picks = rng.choice(len(remaining), size=n_orders, p=remaining / remaining.sum())
        dates.extend(days[start_idx + pick] for pick in picks)
    return dates


def build_orders_and_items(rng, config, customers, products, locations):
    days, weights = day_weights(config)
    city_to_location = dict(zip(locations["city"], locations["location_id"], strict=True))
    location_ids = list(catalog.LOCATIONS)
    location_probs = np.array([share for *_, share in catalog.LOCATIONS.values()])
    location_probs = location_probs / location_probs.sum()

    growth = products["category_id"].map(lambda c: catalog.CATEGORIES[c][1]).to_numpy()
    popularity = products["popularity"].to_numpy()
    prices = products["selling_price"].to_numpy()
    margins = ((products["selling_price"] - products["cost_price"]) / prices).to_numpy()
    product_ids = products["product_id"].to_numpy()

    statuses, status_probs = catalog.ORDER_STATUS_MIX
    order_rows = []
    for customer in customers.itertuples(index=False):
        activity = float(rng.lognormal(mean=-0.18, sigma=0.6))  # some customers buy far more
        payment_methods, payment_probs = catalog.PAYMENT_METHODS[customer.customer_type]
        for order_day in customer_order_dates(rng, customer, activity, days, weights, config):
            if rng.random() < 0.85:
                location_id = city_to_location[customer.city]
            else:
                location_id = str(rng.choice(location_ids, p=location_probs))
            order_rows.append(
                {
                    "customer_id": customer.customer_id,
                    "location_id": location_id,
                    "order_date": order_day.date(),
                    "order_status": str(rng.choice(statuses, p=status_probs)),
                    "payment_method": str(rng.choice(payment_methods, p=payment_probs)),
                    "customer_type": customer.customer_type,
                }
            )

    orders = pd.DataFrame(order_rows)
    orders = orders.sort_values(["order_date", "customer_id"], kind="stable").reset_index(drop=True)
    orders.insert(0, "order_id", [f"O{i + 1:06d}" for i in range(len(orders))])

    item_rows = []
    for order in orders.itertuples(index=False):
        customer_type = order.customer_type
        min_items, max_items = catalog.CUSTOMER_TYPE_ITEMS[customer_type]
        n_items = int(rng.integers(min_items, max_items + 1))
        years = (pd.Timestamp(order.order_date) - pd.Timestamp(config.start)).days / 365
        demand = popularity * np.power(1 + growth, years)
        chosen = rng.choice(len(product_ids), size=n_items, replace=False, p=demand / demand.sum())

        median_qty, sigma = catalog.CUSTOMER_TYPE_QTY[customer_type]
        for idx in chosen:
            # expensive items are bought in smaller quantities
            size_factor = 1.0 if prices[idx] < 300 else 0.6 if prices[idx] < 800 else 0.35
            quantity = min(
                300, max(1, round(rng.lognormal(math.log(median_qty), sigma) * size_factor))
            )
            # never discount a product into a loss
            max_discount = int(max(0, margins[idx] * 100 - 2))
            discount = int(rng.choice(catalog.CUSTOMER_TYPE_DISCOUNTS[customer_type]))
            discount = min(discount, max_discount)
            item_rows.append(
                {
                    "order_item_id": f"OI{len(item_rows) + 1:07d}",
                    "order_id": order.order_id,
                    "product_id": product_ids[idx],
                    "quantity": int(quantity),
                    "unit_price": float(prices[idx]),
                    "discount_pct": float(discount),
                }
            )

    items = pd.DataFrame(item_rows)
    net_amount = items["quantity"] * items["unit_price"] * (1 - items["discount_pct"] / 100)
    orders["order_total"] = orders["order_id"].map(
        net_amount.groupby(items["order_id"]).sum().round(2)
    )
    return orders.drop(columns="customer_type"), items


def build_inventory(rng, config, products, suppliers, locations, orders, items):
    """Current stock for each product and location, based on how fast it sold recently."""
    cutoff = pd.Timestamp(config.snapshot_date) - pd.Timedelta(days=90)
    sales = items.merge(
        orders[["order_id", "location_id", "order_date", "order_status"]], on="order_id"
    )
    recent = sales[
        (sales["order_status"] == "Completed") & (pd.to_datetime(sales["order_date"]) > cutoff)
    ]
    units_sold_90d = recent.groupby(["product_id", "location_id"])["quantity"].sum()

    supplier_lead_time = suppliers.set_index("supplier_id")["lead_time_days"]
    lead_time = dict(
        zip(products["product_id"], products["supplier_id"].map(supplier_lead_time), strict=True)
    )
    scenarios = list(catalog.STOCK_SCENARIOS)

    rows = []
    for product_id in products["product_id"]:
        for location_id in locations["location_id"]:
            if rng.random() > 0.93:  # a few product and location pairs are simply not stocked
                continue
            daily_sales = float(units_sold_90d.get((product_id, location_id), 0)) / 90
            if daily_sales > 0:
                scenario = str(rng.choice(scenarios, p=catalog.STOCK_SCENARIO_PROBS))
                low, high = catalog.STOCK_SCENARIOS[scenario]
                quantity = round(daily_sales * rng.uniform(low, high))
                reorder_level = max(5, math.ceil(daily_sales * (lead_time[product_id] + 7)))
            else:
                # nothing sold here in 90 days: either an empty shelf or dead stock
                quantity = (
                    int(rng.integers(0, 40)) if rng.random() < 0.5 else int(rng.integers(40, 300))
                )
                reorder_level = int(rng.integers(10, 40))
            rows.append(
                {
                    "inventory_id": f"INV{len(rows) + 1:05d}",
                    "product_id": product_id,
                    "location_id": location_id,
                    "quantity_on_hand": int(quantity),
                    "reorder_level": int(reorder_level),
                    "last_restocked_date": config.snapshot_date
                    - timedelta(days=int(rng.integers(2, 60))),
                    "snapshot_date": config.snapshot_date,
                }
            )
    return pd.DataFrame(rows)


def generate_clean_dataset(config=None):
    config = config or SyntheticConfig()
    rng = np.random.default_rng(config.seed)

    categories = build_categories()
    suppliers = build_suppliers()
    locations = build_locations()
    products = build_products(rng)
    customers = build_customers(rng, config)
    orders, items = build_orders_and_items(rng, config, customers, products, locations)
    inventory = build_inventory(rng, config, products, suppliers, locations, orders, items)

    logger.info(
        "Generated %d customers, %d products, %d orders, %d order items, %d inventory rows",
        len(customers),
        len(products),
        len(orders),
        len(items),
        len(inventory),
    )
    return CleanDataset(
        categories,
        suppliers,
        locations,
        products.drop(columns="popularity"),
        customers,
        orders,
        items,
        inventory,
    )
