"""Small helpers for building test tables."""

from datetime import date

import pandas as pd

from src.tables import COLUMNS, RAW_ONLY_COLUMNS

# orders dated after this day count as invalid in the tests
AS_OF = date(2026, 10, 15)


def raw_table(table, *rows):
    """Build a raw table (all text) from dicts. A column left out of a row is missing."""
    columns = COLUMNS[table] + RAW_ONLY_COLUMNS.get(table, [])
    df = pd.DataFrame(list(rows), columns=columns, dtype="str")
    df.insert(0, "source_row", range(2, len(df) + 2))
    return df


def as_list(series):
    """A Series as a plain list with None for missing values, easy to compare in a test."""
    return [None if pd.isna(value) else value for value in series]


def completed_sales_lines(clean):
    """Completed order lines with revenue and profit worked out in pandas.

    The tests compare the SQL views and the API against this independent calculation.
    """
    orders = clean["orders"][clean["orders"]["order_status"] == "Completed"]
    lines = clean["order_items"].merge(orders, on="order_id")
    products = clean["products"][["product_id", "category_id", "cost_price"]]
    lines = lines.merge(products, on="product_id")
    gross = lines["quantity"] * lines["unit_price"] * (1 - lines["discount_pct"] / 100)
    cost = lines["quantity"] * lines["cost_price"]
    return lines.assign(revenue=gross.round(2), profit=(gross - cost).round(2))


def tiny_dataset():
    """One valid row in every table, for the tests that break one thing at a time."""
    day = pd.Timestamp("2026-03-10")
    return {
        "categories": pd.DataFrame({"category_id": ["CAT01"], "category_name": ["Beverages"]}),
        "suppliers": pd.DataFrame(
            {
                "supplier_id": ["S01"],
                "supplier_name": ["Sunrise Beverages"],
                "city": ["Mumbai"],
                "contact_email": ["sales@sunrise.example"],
                "lead_time_days": [5],
            }
        ),
        "locations": pd.DataFrame(
            {
                "location_id": ["L01"],
                "location_name": ["Mumbai Warehouse"],
                "city": ["Mumbai"],
                "state": ["Maharashtra"],
                "region": ["West"],
                "location_type": ["Warehouse"],
            }
        ),
        "products": pd.DataFrame(
            {
                "product_id": ["P0001"],
                "product_name": ["Orange Juice 1L"],
                "category_id": ["CAT01"],
                "supplier_id": ["S01"],
                "cost_price": [80.0],
                "selling_price": [100.0],
                "unit": ["carton"],
            }
        ),
        "customers": pd.DataFrame(
            {
                "customer_id": ["C00001"],
                "customer_name": ["Priya Patel"],
                "email": ["priya@example.com"],
                "phone": ["9876543210"],
                "city": ["Pune"],
                "customer_type": ["Retail"],
                "signup_date": [day],
            }
        ),
        "orders": pd.DataFrame(
            {
                "order_id": ["O000001"],
                "customer_id": ["C00001"],
                "location_id": ["L01"],
                "order_date": [day],
                "order_status": ["Completed"],
                "payment_method": ["UPI"],
            }
        ),
        "order_items": pd.DataFrame(
            {
                "order_item_id": ["OI0000001"],
                "order_id": ["O000001"],
                "product_id": ["P0001"],
                "quantity": [2],
                "unit_price": [100.0],
                "discount_pct": [0.0],
            }
        ),
        "inventory": pd.DataFrame(
            {
                "inventory_id": ["INV00001"],
                "product_id": ["P0001"],
                "location_id": ["L01"],
                "quantity_on_hand": [10],
                "reorder_level": [5],
                "last_restocked_date": [pd.NaT],
                "snapshot_date": [day],
            }
        ),
    }
