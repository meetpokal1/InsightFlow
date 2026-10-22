"""Turn the clean synthetic tables into messy raw exports.

Every table is converted to text first (like a CSV export) and then damaged on purpose.
The manifest returned at the end says how many problems of each kind were injected, so
the pipeline's quality log can be checked against it.
"""

import logging
from collections import defaultdict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

RUPEE = "₹"
BAD_SIGNUP_DATES = ["2025-13-45", "31/02/2025", "N/A", "00-00-0000", "tomorrow"]
BAD_ORDER_DATES = ["2025-02-30", "not available", "31/04/2025", "0000-00-00"]
CITY_ALIASES = {"Mumbai": "Bombay", "Bengaluru": "Bangalore", "Kolkata": "Calcutta"}
CUSTOMER_TYPE_VARIANTS = {
    "Retail": ["retail", "RETAIL", "Retailer", "Retail "],
    "Wholesale": ["wholesale", "Wholesaler", "WHOLESALE", " Wholesale"],
    "Corporate": ["corporate", "Corp", "CORPORATE", "Corporate "],
}
ORDER_STATUS_VARIANTS = {
    "Completed": ["completed", "COMPLETED ", "Complete", "completed "],
    "Cancelled": ["Canceled", "cancelled", "CANCELLED"],
    "Returned": ["returned", "Return", "RETURNED"],
}
PAYMENT_VARIANTS = {
    "UPI": "upi",
    "Credit Card": "CC",
    "Debit Card": "debit card",
    "Net Banking": "netbanking",
}


class Injector:
    """Holds the random generator and counts what was injected."""

    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        self.manifest = defaultdict(dict)

    def pick(self, n, share, minimum=1, exclude=()):
        """Random row positions: about `share` of n rows (at least `minimum`), minus `exclude`."""
        skipped = {int(i) for i in exclude}
        pool = [i for i in range(n) if i not in skipped]
        size = min(max(minimum, round(n * share)), len(pool))
        return self.rng.choice(pool, size=size, replace=False)

    def unique_picker(self, n):
        """Like pick, but never returns a row that an earlier call already returned."""
        used = set()

        def pick_unused(share, minimum=1):
            rows = self.pick(n, share, minimum, exclude=used)
            used.update(int(i) for i in rows)
            return rows

        return pick_unused

    def record(self, table, issue, count):
        counts = self.manifest[table]
        counts[issue] = counts.get(issue, 0) + int(count)

    def choices(self, options, size):
        return [str(x) for x in self.rng.choice(options, size=size)]


def as_text(df):
    """Everything becomes text, the way it would look in a CSV export."""
    return df.astype(str).reset_index(drop=True)


def messy_case(value, kind):
    return {
        "upper": value.upper(),
        "lower": value.lower(),
        "pad": f"  {value} ",
        "double": value.replace(" ", "  "),
    }[kind]


def money_text(value):
    return f"{RUPEE}{float(value):,.2f}"


def mix_date_formats(series, inj, table, column, skip=()):
    """Rewrite about 30% of the ISO dates as dd/mm/yyyy or dd-Mon-yyyy."""
    skipped = {int(i) for i in skip}
    is_iso = series.str.match(r"^\d{4}-\d{2}-\d{2}$").fillna(False).astype(bool)
    candidates = [i for i in series.index[is_iso] if i not in skipped]
    chosen = inj.rng.choice(candidates, size=int(len(candidates) * 0.30), replace=False)
    half = len(chosen) // 2
    slash, month_name = chosen[:half], chosen[half:]
    series = series.copy()
    series.loc[slash] = pd.to_datetime(series.loc[slash]).dt.strftime("%d/%m/%Y")
    series.loc[month_name] = pd.to_datetime(series.loc[month_name]).dt.strftime("%d-%b-%Y")
    inj.record(table, f"mixed_date_formats_{column}", len(chosen))
    return series


def corrupt_categories(df, inj):
    df = as_text(df)
    rows = inj.pick(len(df), 0.45, minimum=2)
    for i in rows:
        kind = inj.rng.choice(["upper", "lower", "pad"])
        df.loc[i, "category_name"] = messy_case(df.loc[i, "category_name"], kind)
    inj.record("categories", "inconsistent_text_formatting", len(rows))

    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    inj.record("categories", "exact_duplicate_rows", 1)
    return df


def corrupt_suppliers(df, inj):
    df = as_text(df)
    rows = inj.pick(len(df), 0.30, minimum=3)
    for i in rows:
        kind = inj.rng.choice(["upper", "lower", "pad"])
        df.loc[i, "city"] = messy_case(df.loc[i, "city"], kind)
    inj.record("suppliers", "inconsistent_text_formatting", len(rows))

    rows = inj.pick(len(df), 0.15, minimum=2)
    df.loc[rows, "contact_email"] = np.nan
    inj.record("suppliers", "missing_contact_email", len(rows))

    rows = inj.pick(len(df), 0.15, minimum=2)
    df.loc[rows, "lead_time_days"] = df.loc[rows, "lead_time_days"] + " days"
    inj.record("suppliers", "lead_time_stored_as_text", len(rows))

    df = pd.concat([df, df.iloc[[2]]], ignore_index=True)
    inj.record("suppliers", "exact_duplicate_rows", 1)
    return df


def corrupt_locations(df, inj):
    df = as_text(df)
    # Bengaluru exported under its old name, Mumbai with extra spaces, Delhi in capitals
    bengaluru = df.index[df["city"] == "Bengaluru"][0]
    df.loc[bengaluru, ["location_name", "city"]] = ["Bangalore Warehouse", "Bangalore"]
    mumbai = df.index[df["city"] == "Mumbai"][0]
    df.loc[mumbai, "location_name"] = "  Mumbai   Warehouse "
    delhi = df.index[df["city"] == "Delhi"][0]
    df.loc[delhi, ["city", "location_name"]] = ["DELHI", "DELHI WAREHOUSE"]
    inj.record("locations", "inconsistent_location_names", 3)

    rows = inj.pick(len(df), 0.40, minimum=2)
    df.loc[rows, "region"] = df.loc[rows, "region"].str.lower()
    inj.record("locations", "inconsistent_text_formatting", len(rows))

    # the same location id appears again under its new name
    duplicate = df.iloc[[bengaluru]].copy()
    duplicate[["location_name", "city"]] = ["Bengaluru Warehouse", "Bengaluru"]
    df = pd.concat([df, duplicate], ignore_index=True)
    inj.record("locations", "duplicate_location_id_conflicting_names", 1)
    return df


def corrupt_products(df, inj):
    df = as_text(df)
    n = len(df)

    rows = inj.pick(n, 0.20)
    for i in rows:
        kind = inj.rng.choice(["pad", "double"])
        df.loc[i, "product_name"] = messy_case(df.loc[i, "product_name"], kind)
    inj.record("products", "inconsistent_text_formatting", len(rows))

    missing_category = inj.pick(n, 0.08, minimum=4)
    df.loc[missing_category, "category_id"] = np.nan
    inj.record("products", "missing_category", len(missing_category))

    bad_category = inj.pick(n, 0.03, minimum=2, exclude=missing_category)
    df.loc[bad_category, "category_id"] = "CAT77"
    inj.record("products", "invalid_category_id", len(bad_category))

    formatted = inj.pick(n, 0.12, minimum=4)
    for i in formatted:
        df.loc[i, "selling_price"] = money_text(df.loc[i, "selling_price"])
        df.loc[i, "cost_price"] = money_text(df.loc[i, "cost_price"])
    inj.record("products", "price_stored_as_formatted_text", len(formatted))

    swapped = inj.pick(n, 0.05, minimum=3, exclude=formatted)
    df.loc[swapped, ["cost_price", "selling_price"]] = df.loc[
        swapped, ["selling_price", "cost_price"]
    ].to_numpy()
    inj.record("products", "cost_price_greater_than_selling_price", len(swapped))

    no_cost = inj.pick(n, 0.04, minimum=2, exclude=[*formatted, *swapped])
    df.loc[no_cost, "cost_price"] = np.nan
    inj.record("products", "missing_cost_price", len(no_cost))

    rows = inj.pick(n, 0.04, minimum=2)
    for i in rows:
        product_id = df.loc[i, "product_id"]
        df.loc[i, "product_id"] = str(inj.rng.choice([product_id.lower(), f" {product_id} "]))
    inj.record("products", "product_id_case_or_whitespace", len(rows))

    rows = inj.pick(n, 0.05, minimum=3)
    df = pd.concat([df, df.iloc[rows]], ignore_index=True)
    inj.record("products", "exact_duplicate_rows", len(rows))
    return df


def corrupt_customers(df, inj):
    """Returns the messy table and a dict {duplicate customer id: original customer id}."""
    df = as_text(df)
    n_original = len(df)

    # the same person registered again under a new id
    source_rows = inj.pick(n_original, 0.05)
    duplicates = df.iloc[source_rows].copy()
    new_ids = [f"C{n_original + 1 + k:05d}" for k in range(len(duplicates))]
    duplicate_map = dict(zip(new_ids, duplicates["customer_id"], strict=True))
    duplicates["customer_id"] = new_ids
    duplicates["customer_name"] = [
        messy_case(name, str(inj.rng.choice(["upper", "lower", "double"])))
        for name in duplicates["customer_name"]
    ]
    duplicates["email"] = [f" {email.upper()} " for email in duplicates["email"]]
    # a third of them lost the email, so only name and phone can match them
    lost_email = inj.rng.choice(len(duplicates), size=len(duplicates) // 3, replace=False)
    duplicates.iloc[lost_email, duplicates.columns.get_loc("email")] = np.nan
    duplicates["phone"] = [f"+91 {phone[:5]} {phone[5:]}" for phone in duplicates["phone"]]
    days_later = pd.to_timedelta(inj.rng.integers(20, 200, len(duplicates)), unit="D").to_numpy()
    new_signup = pd.to_datetime(duplicates["signup_date"]) + days_later
    duplicates["signup_date"] = new_signup.dt.strftime("%Y-%m-%d")
    duplicate_rows = range(n_original, n_original + len(duplicates))
    protected = {*map(int, source_rows), *duplicate_rows}
    df = pd.concat([df, duplicates], ignore_index=True)
    inj.record("customers", "duplicate_customers_new_id", len(duplicates))
    n = len(df)

    # missing values, but not on the rows the duplicate matching relies on
    for column, share, issue in [
        ("email", 0.06, "missing_email"),
        ("phone", 0.08, "missing_phone"),
        ("city", 0.02, "missing_city"),
        ("customer_type", 0.03, "missing_customer_type"),
    ]:
        rows = inj.pick(n, share, exclude=protected)
        df.loc[rows, column] = np.nan
        inj.record("customers", issue, len(rows))

    rows = inj.pick(n, 0.15, exclude=duplicate_rows)
    for i in rows:
        kind = str(inj.rng.choice(["upper", "lower", "pad", "double"]))
        df.loc[i, "customer_name"] = messy_case(df.loc[i, "customer_name"], kind)
    inj.record("customers", "inconsistent_name_formatting", len(rows))

    rows = [i for i in inj.pick(n, 0.20) if isinstance(df.loc[i, "city"], str)]
    for i in rows:
        city = df.loc[i, "city"]
        if city in CITY_ALIASES and inj.rng.random() < 0.5:
            df.loc[i, "city"] = CITY_ALIASES[city]
        else:
            df.loc[i, "city"] = messy_case(city, str(inj.rng.choice(["upper", "lower", "pad"])))
    inj.record("customers", "inconsistent_city_names", len(rows))

    rows = [i for i in inj.pick(n, 0.10) if isinstance(df.loc[i, "customer_type"], str)]
    for i in rows:
        variants = CUSTOMER_TYPE_VARIANTS[df.loc[i, "customer_type"]]
        df.loc[i, "customer_type"] = str(inj.rng.choice(variants))
    inj.record("customers", "inconsistent_customer_type", len(rows))

    invalid = inj.pick(n, 0.02, exclude=protected)
    df["signup_date"] = mix_date_formats(
        df["signup_date"], inj, "customers", "signup_date", invalid
    )
    df.loc[invalid, "signup_date"] = inj.choices(BAD_SIGNUP_DATES, len(invalid))
    inj.record("customers", "invalid_signup_date", len(invalid))

    rows = inj.pick(n_original, 0.01, minimum=3, exclude=protected)
    df = pd.concat([df, df.iloc[rows]], ignore_index=True)
    inj.record("customers", "exact_duplicate_rows", len(rows))
    return df, duplicate_map


def move_orders_to_duplicate_customers(orders, duplicate_map, inj):
    """Some of a customer's orders end up booked under the duplicate customer id."""
    orders = orders.copy()
    moved = 0
    for duplicate_id, original_id in duplicate_map.items():
        rows = orders.index[orders["customer_id"] == original_id]
        if len(rows) == 0:
            continue
        chosen = inj.rng.choice(rows, size=max(1, int(len(rows) * 0.35)), replace=False)
        orders.loc[chosen, "customer_id"] = duplicate_id
        moved += len(chosen)
    inj.record("orders", "orders_booked_under_duplicate_customer_id", moved)
    return orders


def corrupt_orders(df, inj):
    df = as_text(df)
    n = len(df)

    invalid_dates = inj.pick(n, 0.006)
    future_dates = inj.pick(n, 0.002, exclude=invalid_dates)
    df["order_date"] = mix_date_formats(
        df["order_date"], inj, "orders", "order_date", [*invalid_dates, *future_dates]
    )
    df.loc[invalid_dates, "order_date"] = inj.choices(BAD_ORDER_DATES, len(invalid_dates))
    df.loc[future_dates, "order_date"] = "2035-01-15"
    inj.record("orders", "invalid_order_date", len(invalid_dates))
    inj.record("orders", "future_order_date", len(future_dates))

    lowercase = inj.pick(n, 0.02)
    df.loc[lowercase, "customer_id"] = df.loc[lowercase, "customer_id"].str.lower()
    inj.record("orders", "customer_id_case_or_whitespace", len(lowercase))
    unknown = inj.pick(n, 0.005, exclude=lowercase)
    df.loc[unknown, "customer_id"] = "C99999"
    inj.record("orders", "unknown_customer_id", len(unknown))
    missing = inj.pick(n, 0.004, exclude=[*lowercase, *unknown])
    df.loc[missing, "customer_id"] = np.nan
    inj.record("orders", "missing_customer_id", len(missing))

    lowercase = inj.pick(n, 0.01)
    df.loc[lowercase, "location_id"] = df.loc[lowercase, "location_id"].str.lower()
    inj.record("orders", "location_id_case_or_whitespace", len(lowercase))
    unknown = inj.pick(n, 0.003, exclude=lowercase)
    df.loc[unknown, "location_id"] = "L99"
    inj.record("orders", "unknown_location_id", len(unknown))
    missing = inj.pick(n, 0.002, exclude=[*lowercase, *unknown])
    df.loc[missing, "location_id"] = np.nan
    inj.record("orders", "missing_location_id", len(missing))

    rows = inj.pick(n, 0.12)
    for i in rows:
        variants = ORDER_STATUS_VARIANTS[df.loc[i, "order_status"]]
        df.loc[i, "order_status"] = str(inj.rng.choice(variants))
    inj.record("orders", "inconsistent_order_status", len(rows))

    rows = inj.pick(n, 0.04)
    for i in rows:
        method = df.loc[i, "payment_method"]
        df.loc[i, "payment_method"] = PAYMENT_VARIANTS.get(method, method.upper() + " ")
    inj.record("orders", "inconsistent_payment_method", len(rows))
    missing = inj.pick(n, 0.02, exclude=rows)
    df.loc[missing, "payment_method"] = np.nan
    inj.record("orders", "missing_payment_method", len(missing))

    wrong = inj.pick(n, 0.03)
    factors = inj.rng.choice([0.9, 1.1], len(wrong))
    wrong_totals = (df.loc[wrong, "order_total"].astype(float) * factors).round(2)
    df.loc[wrong, "order_total"] = wrong_totals.astype(str)
    inj.record("orders", "order_total_does_not_match_items", len(wrong))
    missing = inj.pick(n, 0.02, exclude=wrong)
    df.loc[missing, "order_total"] = np.nan
    inj.record("orders", "missing_order_total", len(missing))
    formatted = inj.pick(n, 0.10, exclude=[*wrong, *missing])
    df.loc[formatted, "order_total"] = [money_text(v) for v in df.loc[formatted, "order_total"]]
    inj.record("orders", "order_total_stored_as_formatted_text", len(formatted))

    rows = inj.pick(n, 0.012)
    df = pd.concat([df, df.iloc[rows]], ignore_index=True)
    inj.record("orders", "exact_duplicate_rows", len(rows))
    return df


def corrupt_order_items(df, inj):
    df = as_text(df)
    n = len(df)
    pick = inj.unique_picker(n)

    rows = pick(0.02)
    df.loc[rows, "product_id"] = [
        v.lower() if inj.rng.random() < 0.5 else f" {v} " for v in df.loc[rows, "product_id"]
    ]
    inj.record("order_items", "product_id_case_or_whitespace", len(rows))
    rows = pick(0.004)
    df.loc[rows, "product_id"] = inj.choices(["P9999", "PRD-12", "UNKNOWN", "P0000"], len(rows))
    inj.record("order_items", "invalid_product_id", len(rows))
    rows = pick(0.002)
    df.loc[rows, "order_id"] = "O999999"
    inj.record("order_items", "orphan_order_id", len(rows))

    rows = pick(0.006)
    df.loc[rows, "quantity"] = "-" + df.loc[rows, "quantity"]
    inj.record("order_items", "negative_quantity", len(rows))
    rows = pick(0.002)
    df.loc[rows, "quantity"] = "0"
    inj.record("order_items", "zero_quantity", len(rows))
    rows = pick(0.003)
    df.loc[rows, "quantity"] = np.nan
    inj.record("order_items", "missing_quantity", len(rows))
    rows = pick(0.03)
    df.loc[rows, "quantity"] = df.loc[rows, "quantity"] + ".0"
    inj.record("order_items", "quantity_stored_as_decimal_text", len(rows))
    rows = pick(0.002)
    df.loc[rows, "quantity"] = inj.choices(["5000", "12000", "25000"], len(rows))
    inj.record("order_items", "quantity_outlier", len(rows))

    rows = pick(0.01)
    df.loc[rows, "unit_price"] = np.nan
    inj.record("order_items", "missing_unit_price", len(rows))
    rows = pick(0.05)
    df.loc[rows, "unit_price"] = [money_text(v) for v in df.loc[rows, "unit_price"]]
    inj.record("order_items", "unit_price_stored_as_formatted_text", len(rows))
    rows = pick(0.003)
    factors = inj.rng.choice([100.0, 0.01], len(rows))  # misplaced decimal point
    shifted = (df.loc[rows, "unit_price"].astype(float) * factors).round(2)
    df.loc[rows, "unit_price"] = shifted.astype(str)
    inj.record("order_items", "unit_price_outlier", len(rows))

    rows = pick(0.02)
    df.loc[rows, "discount_pct"] = np.nan
    inj.record("order_items", "missing_discount", len(rows))
    rows = pick(0.03)
    whole_percent = df.loc[rows, "discount_pct"].astype(float).astype(int).astype(str)
    df.loc[rows, "discount_pct"] = whole_percent + "%"
    inj.record("order_items", "discount_stored_with_percent_sign", len(rows))
    rows = pick(0.002)
    df.loc[rows, "discount_pct"] = inj.choices(["150", "-5"], len(rows))
    inj.record("order_items", "invalid_discount", len(rows))

    rows = inj.pick(n, 0.01)
    df = pd.concat([df, df.iloc[rows]], ignore_index=True)
    inj.record("order_items", "exact_duplicate_rows", len(rows))
    return df


def corrupt_inventory(df, inj):
    df = as_text(df)
    n = len(df)
    pick = inj.unique_picker(n)

    rows = pick(0.02)
    df.loc[rows, "product_id"] = df.loc[rows, "product_id"].str.lower()
    inj.record("inventory", "product_id_case_or_whitespace", len(rows))
    rows = pick(0.012)
    df.loc[rows, "product_id"] = "P9998"
    inj.record("inventory", "invalid_product_id", len(rows))
    rows = pick(0.015)
    df.loc[rows, "quantity_on_hand"] = "-" + (
        df.loc[rows, "quantity_on_hand"].astype(int) + 3
    ).astype(str)
    inj.record("inventory", "negative_quantity_on_hand", len(rows))
    rows = pick(0.03)
    df.loc[rows, "quantity_on_hand"] = df.loc[rows, "quantity_on_hand"] + " units"
    inj.record("inventory", "quantity_stored_with_unit_text", len(rows))
    rows = pick(0.04)
    df.loc[rows, "reorder_level"] = np.nan
    inj.record("inventory", "missing_reorder_level", len(rows))
    invalid = pick(0.01)
    df.loc[invalid, "last_restocked_date"] = "2026-02-31"
    inj.record("inventory", "invalid_last_restocked_date", len(invalid))
    rows = pick(0.20)
    restocked = pd.to_datetime(df.loc[rows, "last_restocked_date"])
    df.loc[rows, "last_restocked_date"] = restocked.dt.strftime("%d/%m/%Y")
    inj.record("inventory", "mixed_date_formats_last_restocked_date", len(rows))

    # a stale second row for the same product and location: older restock date, wrong quantity
    rows = pick(0.02)
    stale = df.iloc[rows].copy()
    stale["inventory_id"] = [f"INV{n + 1 + k:05d}" for k in range(len(stale))]
    stale["quantity_on_hand"] = "999"
    stale["last_restocked_date"] = "2026-01-05"
    df = pd.concat([df, stale], ignore_index=True)
    inj.record("inventory", "stale_duplicate_product_location_row", len(stale))
    return df


def corrupt_dataset(clean, seed=7):
    """Return ({table name: messy text DataFrame}, manifest of injected problems)."""
    inj = Injector(seed)
    customers, duplicate_map = corrupt_customers(clean.customers, inj)
    orders = move_orders_to_duplicate_customers(clean.orders, duplicate_map, inj)
    messy = {
        "categories": corrupt_categories(clean.categories, inj),
        "suppliers": corrupt_suppliers(clean.suppliers, inj),
        "locations": corrupt_locations(clean.locations, inj),
        "products": corrupt_products(clean.products, inj),
        "customers": customers,
        "orders": corrupt_orders(orders, inj),
        "order_items": corrupt_order_items(clean.order_items, inj),
        "inventory": corrupt_inventory(clean.inventory, inj),
    }
    total = sum(sum(counts.values()) for counts in inj.manifest.values())
    logger.info("Injected %d data problems across %d tables", total, len(messy))
    return messy, {table: dict(counts) for table, counts in inj.manifest.items()}
