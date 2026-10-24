"""The PostgreSQL schema, the loader and the views, using the small test dataset."""

import math

import pandas as pd
import pytest
from pandas.errors import DatabaseError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.database.loader import load_tables
from tests.helpers import completed_sales_lines

pytestmark = pytest.mark.db

ORDER_COLUMNS = "order_id, customer_id, location_id, order_date, order_status, payment_method"
LINE_COLUMNS = "order_item_id, order_id, product_id, quantity, unit_price, discount_pct"
STOCK_COLUMNS = (
    "inventory_id, product_id, location_id, quantity_on_hand, reorder_level, "
    "last_restocked_date, snapshot_date"
)

# each statement breaks one rule of the schema and must be refused by PostgreSQL
BROKEN_ROWS = {
    "order for an unknown customer": f"""
        INSERT INTO orders ({ORDER_COLUMNS})
        VALUES ('O_TEST', 'NOBODY', 'L01', '2026-01-01', 'Completed', 'UPI')""",
    "order with an unknown status": f"""
        INSERT INTO orders ({ORDER_COLUMNS})
        SELECT 'O_TEST', customer_id, 'L01', '2026-01-01', 'Pending', 'UPI'
        FROM customers LIMIT 1""",
    "order line with zero quantity": f"""
        INSERT INTO order_items ({LINE_COLUMNS})
        SELECT 'OI_TEST', order_id, 'P0001', 0, 10, 0 FROM orders LIMIT 1""",
    "order line with a discount above 100": f"""
        INSERT INTO order_items ({LINE_COLUMNS})
        SELECT 'OI_TEST', order_id, 'P0001', 1, 10, 101 FROM orders LIMIT 1""",
    "negative stock": f"""
        INSERT INTO inventory ({STOCK_COLUMNS})
        VALUES ('INV_TEST', 'P0001', 'L01', -1, 0, NULL, '2000-01-01')""",
    "stock row repeated for the same snapshot": f"""
        INSERT INTO inventory ({STOCK_COLUMNS})
        SELECT 'INV_TEST', product_id, location_id, 1, 1, NULL, snapshot_date
        FROM inventory LIMIT 1""",
    "cost above the selling price": """
        UPDATE products SET cost_price = selling_price + 1 WHERE product_id = 'P0001'""",
    "product id that already exists": "INSERT INTO products SELECT * FROM products LIMIT 1",
}


def scalar(engine, sql):
    with engine.connect() as connection:
        return connection.execute(text(sql)).scalar_one()


def test_every_cleaned_table_is_in_the_database(database, cleaned):
    for name, df in cleaned.clean.items():
        assert scalar(database, f"SELECT COUNT(*) FROM {name}") == len(df)


def test_the_quality_log_is_stored(database, cleaned):
    assert scalar(database, "SELECT COUNT(*) FROM etl_quality_log") == len(cleaned.quality_log)


@pytest.mark.parametrize("statement", BROKEN_ROWS.values(), ids=BROKEN_ROWS.keys())
def test_the_schema_refuses_data_that_breaks_a_rule(database, statement):
    with pytest.raises(IntegrityError):
        with database.begin() as connection:
            connection.execute(text(statement))


def test_a_failed_load_leaves_the_existing_data_in_place(database, cleaned):
    broken = {**cleaned.clean, "order_items": cleaned.clean["order_items"].assign(product_id="X")}
    with pytest.raises(DatabaseError):  # pandas wraps the foreign key error
        load_tables(database, broken)
    for name, df in cleaned.clean.items():
        assert scalar(database, f"SELECT COUNT(*) FROM {name}") == len(df)


def test_loading_again_replaces_the_rows_instead_of_adding_to_them(database, cleaned):
    load_tables(database, cleaned.clean)
    for name, df in cleaned.clean.items():
        assert scalar(database, f"SELECT COUNT(*) FROM {name}") == len(df)


def test_calendar_table_has_a_row_for_every_order_date(database):
    missing = scalar(
        database,
        """
        SELECT COUNT(*) FROM orders AS o
        LEFT JOIN dim_date AS d ON d.date_key = o.order_date
        WHERE d.date_key IS NULL
        """,
    )
    assert missing == 0


def test_sales_view_only_contains_completed_orders(database, cleaned):
    other_statuses = scalar(
        database,
        """
        SELECT COUNT(*) FROM vw_fact_sales AS f
        JOIN orders AS o ON o.order_id = f.order_id
        WHERE o.order_status <> 'Completed'
        """,
    )
    assert other_statuses == 0
    assert scalar(database, "SELECT COUNT(*) FROM vw_fact_sales") == len(
        completed_sales_lines(cleaned.clean)
    )


def test_sales_view_revenue_and_profit_match_pandas(database, cleaned):
    lines = completed_sales_lines(cleaned.clean)
    revenue = scalar(database, "SELECT SUM(net_revenue) FROM vw_fact_sales")
    profit = scalar(database, "SELECT SUM(gross_profit) FROM vw_fact_sales")
    assert float(revenue) == pytest.approx(lines["revenue"].sum(), rel=1e-6)
    assert float(profit) == pytest.approx(lines["profit"].sum(), rel=1e-6)


def test_units_sold_in_the_last_90_days_match_pandas(database, cleaned):
    lines = completed_sales_lines(cleaned.clean)
    snapshot = cleaned.clean["inventory"]["snapshot_date"].max()
    recent = lines[lines["order_date"] > snapshot - pd.Timedelta(days=90)]
    expected = recent.groupby(["product_id", "location_id"])["quantity"].sum()

    view = pd.read_sql_query(
        "SELECT product_id, location_id, units_sold_90d FROM vw_fact_inventory", database
    ).set_index(["product_id", "location_id"])["units_sold_90d"]
    # the view has one row per stock record, so a product never sold at a location is 0
    assert view.to_dict() == expected.reindex(view.index, fill_value=0).to_dict()


def test_stock_status_follows_the_documented_rules(database):
    stock = pd.read_sql_query("SELECT * FROM vw_fact_inventory", database)
    stock["cover"] = stock["quantity_on_hand"] * 90 / stock["units_sold_90d"]  # inf when 0 sold
    selling = stock[stock["units_sold_90d"] > 0]
    status = selling["stock_status"]

    assert set(stock["stock_status"]) <= {
        "No recent sales",
        "Out of stock",
        "Stock-out risk",
        "Low stock",
        "Overstocked",
        "Healthy",
    }
    assert (stock.loc[stock["units_sold_90d"] == 0, "stock_status"] == "No recent sales").all()
    assert (status[selling["quantity_on_hand"] == 0] == "Out of stock").all()

    risk = selling[status == "Stock-out risk"]
    assert (risk["cover"] < risk["lead_time_days"]).all()
    assert (risk["quantity_on_hand"] > 0).all()

    low = selling[status == "Low stock"]
    assert (low["quantity_on_hand"] <= low["reorder_level"]).all()
    assert (low["cover"] >= low["lead_time_days"]).all()

    overstocked = selling[status == "Overstocked"]
    assert (overstocked["cover"] > 180).all()

    healthy = selling[status == "Healthy"]
    assert (healthy["quantity_on_hand"] > healthy["reorder_level"]).all()
    assert healthy["cover"].between(healthy["lead_time_days"], 180).all()


def test_suggested_order_covers_the_lead_time_plus_30_days_and_is_never_negative(database):
    stock = pd.read_sql_query("SELECT * FROM vw_fact_inventory", database)
    needed = (stock["avg_daily_units"] * (stock["lead_time_days"] + 30)).round(6).map(math.ceil)
    expected = (needed - stock["quantity_on_hand"]).clip(lower=0)
    assert stock["suggested_order_qty"].astype(float).tolist() == expected.astype(float).tolist()
    assert (stock["suggested_order_qty"] >= 0).all()
    assert (stock["suggested_order_qty"] > 0).any()


def test_customer_dimension_has_every_customer_and_marks_those_without_purchases(database, cleaned):
    customers = pd.read_sql_query("SELECT customer_id, segment FROM vw_dim_customer", database)
    all_ids = set(cleaned.clean["customers"]["customer_id"])
    buyers = set(completed_sales_lines(cleaned.clean)["customer_id"])
    assert len(customers) == len(all_ids)
    never_bought = set(customers.loc[customers["segment"] == "No purchases", "customer_id"])
    assert never_bought == all_ids - buyers


def test_customer_segments_follow_the_rfm_rules(database, cleaned):
    segments = pd.read_sql_query("SELECT * FROM vw_customer_segments", database)
    buyers = completed_sales_lines(cleaned.clean)["customer_id"].nunique()
    assert len(segments) == buyers
    assert segments["customer_id"].is_unique

    expected_frequency = pd.cut(segments["orders"], [0, 1, 4, 9, float("inf")], labels=[1, 2, 3, 4])
    assert (segments["frequency_score"] == expected_frequency.astype(int)).all()

    # the more recent the last order, the higher the recency score
    oldest_per_score = segments.groupby("recency_score")["recency_days"].max()
    assert oldest_per_score.is_monotonic_decreasing

    segment = segments["segment"]
    recent = segments["recency_score"] >= 3
    frequent = segments["frequency_score"] >= 3
    assert (recent & frequent)[segment == "Champions"].all()
    assert (~recent & frequent)[segment == "At risk"].all()
    assert (recent & (segments["frequency_score"] == 1))[segment == "New or one-time"].all()
    assert (segments["recency_score"] == 1)[segment == "Lost"].all()
    assert not ((recent & frequent) & (segment != "Champions")).any()


def test_data_assurance_reconciliation_view_matches_tables_and_log(database):
    recon = pd.read_sql_query('SELECT * FROM data_assurance_reconciliation', database)
    assert len(recon) == 8
    expected_tables = [
        'categories',
        'suppliers',
        'locations',
        'products',
        'customers',
        'orders',
        'order_items',
        'inventory',
    ]
    assert list(recon['table_name']) == expected_tables
    assert (recon['reconciliation_status'] == 'BALANCED').all()
    assert (recon['raw_ingested'] >= recon['clean_loaded']).all()
    assert (recon['preservation_rate'] > 0).all()
