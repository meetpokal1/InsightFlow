"""Run every table cleaner in the order the tables depend on each other."""

import pandas as pd

from src.cleaning.common import finish
from src.cleaning.customers import clean_customers
from src.cleaning.inventory import clean_inventory
from src.cleaning.products import clean_products
from src.cleaning.reference import clean_categories, clean_locations, clean_suppliers
from src.cleaning.sales import (
    clean_order_items,
    clean_orders,
    drop_orders_without_items,
    finish_orders,
)


def clean_all_tables(raw, as_of, log):
    """Clean the eight raw tables.

    Returns two dicts keyed by table name: the clean tables and the rejected rows.
    """
    clean = {}
    rejected = {}

    clean["categories"], rejected["categories"] = clean_categories(raw["categories"], log)
    clean["suppliers"], rejected["suppliers"] = clean_suppliers(raw["suppliers"], log)
    clean["locations"], rejected["locations"] = clean_locations(raw["locations"], log)
    clean["products"], rejected["products"] = clean_products(
        raw["products"],
        clean["categories"]["category_id"],
        clean["suppliers"]["supplier_id"],
        log,
    )
    clean["customers"], rejected["customers"], duplicate_ids = clean_customers(
        raw["customers"], as_of, log
    )

    orders, rejected_orders = clean_orders(
        raw["orders"],
        clean["customers"]["customer_id"],
        clean["locations"]["location_id"],
        duplicate_ids,
        as_of,
        log,
    )
    items, rejected["order_items"] = clean_order_items(
        raw["order_items"], orders["order_id"], clean["products"], log
    )
    orders, orders_without_items = drop_orders_without_items(orders, items, log)
    rejected["orders"] = pd.concat([rejected_orders, orders_without_items], ignore_index=True)
    clean["orders"] = finish_orders(orders, items, log)
    clean["order_items"] = finish(items, "order_items")

    clean["inventory"], rejected["inventory"] = clean_inventory(
        raw["inventory"], clean["products"], clean["locations"]["location_id"], log
    )
    return clean, rejected
