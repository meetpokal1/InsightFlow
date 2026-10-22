"""Cleaning for orders and order items."""

import pandas as pd

from src.cleaning.common import drop_exact_duplicates, finish
from src.cleaning.parsing import parse_dates, to_number
from src.cleaning.quality import Quarantine
from src.cleaning.rules import (
    DEFAULT_PAYMENT_METHOD,
    MAX_ORDER_QUANTITY,
    ORDER_DATE_MIN,
    ORDER_STATUSES,
    PAYMENT_METHODS,
    PRICE_OUTLIER_RATIO,
)
from src.cleaning.text import map_vocabulary, normalize_id, remap_ids
from src.cleaning.validators import find_orphans

# the order total is only compared with the items, so a rupee of rounding is ignored
TOTAL_TOLERANCE = 1.0


def clean_orders(raw, customer_ids, location_ids, customer_id_map, as_of, log):
    """Clean the order headers. The raw order_total is kept as raw_order_total for now."""
    quarantine = Quarantine("orders", log)
    df = drop_exact_duplicates(raw, "orders", log)

    customer_id = normalize_id(df["customer_id"])
    remapped = remap_ids(customer_id, customer_id_map)
    log.add(
        "orders", "customer_id_of_duplicate_customer", (customer_id != remapped).sum(), "remapped"
    )

    df = df.assign(
        order_id=normalize_id(df["order_id"]),
        customer_id=remapped,
        location_id=normalize_id(df["location_id"]),
        order_date=parse_dates(df["order_date"]),
        order_status=map_vocabulary(df["order_status"], ORDER_STATUSES),
        payment_method=map_vocabulary(df["payment_method"], PAYMENT_METHODS),
        raw_order_total=to_number(df["order_total"]),
    )
    df = quarantine.reject(df, df["order_id"].isna(), "missing_order_id")
    df = quarantine.reject(df, df.duplicated("order_id"), "duplicate_order_id")
    df = quarantine.reject(df, df["order_date"].isna(), "invalid_order_date")
    too_early = df["order_date"] < pd.Timestamp(ORDER_DATE_MIN)
    too_late = df["order_date"] > pd.Timestamp(as_of)
    df = quarantine.reject(df, too_early | too_late, "order_date_out_of_range")
    df = quarantine.reject(df, df["order_status"].isna(), "unknown_order_status")

    df = quarantine.reject(df, df["customer_id"].isna(), "missing_customer_id")
    orphans = find_orphans(df["customer_id"], customer_ids)
    df = quarantine.reject(df, orphans, "unknown_customer_id")
    df = quarantine.reject(df, df["location_id"].isna(), "missing_location_id")
    orphans = find_orphans(df["location_id"], location_ids)
    df = quarantine.reject(df, orphans, "unknown_location_id")

    no_payment = df["payment_method"].isna()
    log.add("orders", "missing_or_unknown_payment_method", no_payment.sum(), "set to Unknown")
    df = df.assign(payment_method=df["payment_method"].fillna(DEFAULT_PAYMENT_METHOD))
    return df, quarantine.frame()


def clean_order_items(raw, order_ids, products, log):
    """Clean the order lines. `products` supplies the list price used to repair bad prices."""
    quarantine = Quarantine("order_items", log)
    list_prices = products.set_index("product_id")["selling_price"]
    df = drop_exact_duplicates(raw, "order_items", log)
    df = df.assign(
        order_item_id=normalize_id(df["order_item_id"]),
        order_id=normalize_id(df["order_id"]),
        product_id=normalize_id(df["product_id"]),
        quantity=to_number(df["quantity"]),
        unit_price=to_number(df["unit_price"]),
        discount_pct=to_number(df["discount_pct"]),
    )
    df = quarantine.reject(df, df["order_item_id"].isna(), "missing_order_item_id")
    df = quarantine.reject(df, df.duplicated("order_item_id"), "duplicate_order_item_id")
    # this also catches the lines of orders that were rejected earlier
    df = quarantine.reject(df, ~df["order_id"].isin(set(order_ids)), "order_not_found")
    df = quarantine.reject(df, ~df["product_id"].isin(list_prices.index), "unknown_product_id")

    df = quarantine.reject(df, df["quantity"].isna(), "missing_quantity")
    df = quarantine.reject(df, df["quantity"] % 1 != 0, "non_integer_quantity")
    negative = df["quantity"] < 0
    log.add("order_items", "negative_quantity", negative.sum(), "sign flipped (typing error)")
    df = df.assign(quantity=df["quantity"].abs())
    df = quarantine.reject(df, df["quantity"] == 0, "zero_quantity")
    df = quarantine.reject(df, df["quantity"] > MAX_ORDER_QUANTITY, "quantity_outlier")

    list_price = df["product_id"].map(list_prices)
    no_price = ~(df["unit_price"] > 0)
    ratio = df["unit_price"] / list_price
    price_outlier = ~no_price & ((ratio > PRICE_OUTLIER_RATIO) | (ratio < 1 / PRICE_OUTLIER_RATIO))
    log.add("order_items", "missing_unit_price", no_price.sum(), "set to the list price")
    log.add("order_items", "unit_price_outlier", price_outlier.sum(), "set to the list price")
    df = df.assign(unit_price=df["unit_price"].mask(no_price | price_outlier, list_price))

    no_discount = df["discount_pct"].isna()
    bad_discount = ~no_discount & ~df["discount_pct"].between(0, 100)
    log.add("order_items", "missing_discount", no_discount.sum(), "set to 0")
    log.add("order_items", "invalid_discount", bad_discount.sum(), "set to 0")
    df = df.assign(discount_pct=df["discount_pct"].mask(no_discount | bad_discount, 0))

    df = df.assign(
        quantity=df["quantity"].astype("int64"),
        unit_price=df["unit_price"].round(2),
        discount_pct=df["discount_pct"].round(2),
    )
    return df, quarantine.frame()


def drop_orders_without_items(orders, items, log):
    """An order whose lines were all rejected has nothing left to analyse."""
    quarantine = Quarantine("orders", log)
    has_no_items = ~orders["order_id"].isin(set(items["order_id"]))
    orders = quarantine.reject(orders, has_no_items, "order_without_valid_items")
    return orders, quarantine.frame()


def line_net_amount(items):
    """Quantity x unit price after the line discount."""
    return items["quantity"] * items["unit_price"] * (1 - items["discount_pct"] / 100)


def finish_orders(orders, items, log):
    """Compare the order totals in the raw file with the lines, then drop the raw total.

    The lines are the source of truth. The total is only used as a cross-check, so
    a mismatch is logged and nothing is changed.
    """
    from_items = orders["order_id"].map(line_net_amount(items).groupby(items["order_id"]).sum())
    stated = orders["raw_order_total"]
    mismatch = stated.notna() & ((stated - from_items).abs() > TOTAL_TOLERANCE)
    log.add(
        "orders", "order_total_differs_from_lines", mismatch.sum(), "kept the lines, ignored total"
    )
    log.add("orders", "missing_order_total", stated.isna().sum(), "none needed, total is derived")
    return finish(orders, "orders")
