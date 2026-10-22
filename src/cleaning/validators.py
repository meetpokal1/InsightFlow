"""Checks used by the cleaners, and the final check that runs before anything is loaded."""

from src.cleaning.rules import (
    MAX_ORDER_QUANTITY,
    VALID_CUSTOMER_TYPES,
    VALID_LOCATION_TYPES,
    VALID_ORDER_STATUSES,
    VALID_REGIONS,
)
from src.tables import COLUMNS, FOREIGN_KEYS, PRIMARY_KEYS

EMAIL_PATTERN = r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$"

# columns that must have a value (the SQL schema declares them NOT NULL as well)
REQUIRED_COLUMNS = {
    "categories": ["category_name"],
    "suppliers": ["supplier_name", "lead_time_days"],
    "locations": ["location_name", "region", "location_type"],
    "products": ["product_name", "category_id", "supplier_id", "cost_price", "selling_price"],
    "customers": ["customer_name", "customer_type"],
    "orders": ["customer_id", "location_id", "order_date", "order_status", "payment_method"],
    "order_items": ["order_id", "product_id", "quantity", "unit_price", "discount_pct"],
    "inventory": [
        "product_id",
        "location_id",
        "quantity_on_hand",
        "reorder_level",
        "snapshot_date",
    ],
}

# (table, what must be true, function returning True for the rows that break it)
VALUE_RULES = [
    ("locations", "region is a known region", lambda df: ~df["region"].isin(VALID_REGIONS)),
    (
        "locations",
        "location_type is Store or Warehouse",
        lambda df: ~df["location_type"].isin(VALID_LOCATION_TYPES),
    ),
    ("products", "selling_price is positive", lambda df: ~(df["selling_price"] > 0)),
    (
        "products",
        "cost_price is between 0 and selling_price",
        lambda df: ~((df["cost_price"] >= 0) & (df["cost_price"] <= df["selling_price"])),
    ),
    (
        "customers",
        "customer_type is a known type",
        lambda df: ~df["customer_type"].isin(VALID_CUSTOMER_TYPES),
    ),
    (
        "orders",
        "order_status is a known status",
        lambda df: ~df["order_status"].isin(VALID_ORDER_STATUSES),
    ),
    (
        "order_items",
        f"quantity is between 1 and {MAX_ORDER_QUANTITY}",
        lambda df: ~df["quantity"].between(1, MAX_ORDER_QUANTITY),
    ),
    ("order_items", "unit_price is positive", lambda df: ~(df["unit_price"] > 0)),
    (
        "order_items",
        "discount_pct is between 0 and 100",
        lambda df: ~df["discount_pct"].between(0, 100),
    ),
    ("inventory", "quantity_on_hand is not negative", lambda df: ~(df["quantity_on_hand"] >= 0)),
    ("inventory", "reorder_level is not negative", lambda df: ~(df["reorder_level"] >= 0)),
]


class DataValidationError(Exception):
    """Raised when the cleaned data still breaks a key, relationship or value rule."""


def is_valid_email(series):
    """True where the text looks like an email address (missing values count as False)."""
    return series.astype("string").str.match(EMAIL_PATTERN).fillna(False).astype(bool)


def find_orphans(child, parent_keys):
    """True for child values that are filled in but do not exist among the parent keys."""
    return child.notna() & ~child.isin(set(parent_keys))


def validate_dataset(tables):
    """Check the cleaned tables and return a list of problems (an empty list means OK)."""
    problems = []

    for table, columns in COLUMNS.items():
        if list(tables[table].columns) != columns:
            problems.append(f"{table}: columns do not match the data model")
    if problems:
        return problems  # the checks below rely on the column names

    for table, key in PRIMARY_KEYS.items():
        df = tables[table]
        if df[key].isna().any():
            problems.append(f"{table}: {df[key].isna().sum()} missing values in {key}")
        if df[key].duplicated().any():
            problems.append(f"{table}: {df[key].duplicated().sum()} duplicate values in {key}")

    for table, columns in REQUIRED_COLUMNS.items():
        for column in columns:
            missing = tables[table][column].isna().sum()
            if missing:
                problems.append(f"{table}: {missing} missing values in required column {column}")

    for child, column, parent in FOREIGN_KEYS:
        parent_keys = tables[parent][PRIMARY_KEYS[parent]]
        orphans = ~tables[child][column].isin(set(parent_keys))
        if orphans.any():
            problems.append(f"{child}.{column}: {orphans.sum()} values not found in {parent}")

    for table, rule, broken in VALUE_RULES:
        count = broken(tables[table]).sum()
        if count:
            problems.append(f"{table}: {count} rows where {rule} is not true")
    return problems


def assert_valid(tables):
    problems = validate_dataset(tables)
    if problems:
        raise DataValidationError("; ".join(problems))
