"""The data model in one place: tables, columns, primary keys and foreign keys.

The cleaners, the validator and the database loader all read from here.
The matching SQL is in sql/schema/.
"""

# parents come before children, so this is also a safe load order
TABLE_LOAD_ORDER = [
    "categories",
    "suppliers",
    "locations",
    "products",
    "customers",
    "orders",
    "order_items",
    "inventory",
]

COLUMNS = {
    "categories": ["category_id", "category_name"],
    "suppliers": ["supplier_id", "supplier_name", "city", "contact_email", "lead_time_days"],
    "locations": ["location_id", "location_name", "city", "state", "region", "location_type"],
    "products": [
        "product_id",
        "product_name",
        "category_id",
        "supplier_id",
        "cost_price",
        "selling_price",
        "unit",
    ],
    "customers": [
        "customer_id",
        "customer_name",
        "email",
        "phone",
        "city",
        "customer_type",
        "signup_date",
    ],
    "orders": [
        "order_id",
        "customer_id",
        "location_id",
        "order_date",
        "order_status",
        "payment_method",
    ],
    "order_items": [
        "order_item_id",
        "order_id",
        "product_id",
        "quantity",
        "unit_price",
        "discount_pct",
    ],
    "inventory": [
        "inventory_id",
        "product_id",
        "location_id",
        "quantity_on_hand",
        "reorder_level",
        "last_restocked_date",
        "snapshot_date",
    ],
}

# columns the raw files must have besides COLUMNS. They are read, but not loaded into PostgreSQL.
RAW_ONLY_COLUMNS = {"orders": ["order_total"]}

PRIMARY_KEYS = {
    "categories": "category_id",
    "suppliers": "supplier_id",
    "locations": "location_id",
    "products": "product_id",
    "customers": "customer_id",
    "orders": "order_id",
    "order_items": "order_item_id",
    "inventory": "inventory_id",
}

# (child table, child column, parent table); the parent column is the parent's primary key
FOREIGN_KEYS = [
    ("products", "category_id", "categories"),
    ("products", "supplier_id", "suppliers"),
    ("orders", "customer_id", "customers"),
    ("orders", "location_id", "locations"),
    ("order_items", "order_id", "orders"),
    ("order_items", "product_id", "products"),
    ("inventory", "product_id", "products"),
    ("inventory", "location_id", "locations"),
]
