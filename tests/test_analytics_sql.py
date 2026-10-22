"""The SQL files in sql/analytics/ run against the test database and give consistent answers."""

import pandas as pd
import pytest
from sqlalchemy import text

from src.analytics.runner import ANALYTICS_DIR, list_queries, run_all
from tests.helpers import completed_sales_lines

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def results(database):
    return run_all(database)


@pytest.fixture(scope="module")
def lines(cleaned):
    return completed_sales_lines(cleaned.clean)


def test_every_query_file_runs_and_returns_columns(results):
    assert len(results) == len(list_queries()) >= 15
    for name, df in results.items():
        assert isinstance(df, pd.DataFrame) and len(df.columns) > 1, name


def test_monthly_revenue_adds_up_to_the_total(results, lines):
    monthly = results["01_monthly_revenue"]
    assert monthly["revenue"].sum() == pytest.approx(lines["revenue"].sum(), rel=1e-6)
    assert monthly["orders"].sum() == lines["order_id"].nunique()
    assert monthly["month"].is_monotonic_increasing


def test_monthly_growth_is_the_change_from_the_month_before(results):
    growth = results["02_monthly_growth"].reset_index(drop=True)
    assert pd.isna(growth.loc[0, "mom_growth_pct"])
    expected = 100 * (growth.loc[5, "revenue"] / growth.loc[4, "revenue"] - 1)
    assert growth.loc[5, "mom_growth_pct"] == pytest.approx(expected, abs=0.06)


def run_after_deleting_lines(database, query_file, delete_sql, params):
    """Run a query inside a transaction that removed some sales first, then roll it back."""
    query = text((ANALYTICS_DIR / query_file).read_text())
    with database.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text(delete_sql), params)
            return pd.read_sql_query(query, connection)
        finally:
            transaction.rollback()


def test_a_month_without_sales_is_listed_with_zero_revenue_and_does_not_shift_the_growth(
    database, results
):
    full = results["02_monthly_growth"].reset_index(drop=True)
    gap = full.loc[5, "month"]
    delete_lines = """
        DELETE FROM order_items WHERE order_id IN (
            SELECT order_id FROM orders WHERE date_trunc('month', order_date)::date = :month
        )
    """
    growth = run_after_deleting_lines(
        database, "02_monthly_growth.sql", delete_lines, {"month": gap}
    ).reset_index(drop=True)

    assert growth["month"].tolist() == full["month"].tolist()
    assert growth.loc[5, "revenue"] == 0
    assert growth.loc[5, "mom_growth_pct"] == -100
    assert pd.isna(growth.loc[6, "mom_growth_pct"])
    assert pd.isna(growth.loc[17, "yoy_growth_pct"])
    # the months after the gap still compare with the month right before them
    expected = 100 * (growth.loc[8, "revenue"] / growth.loc[7, "revenue"] - 1)
    assert growth.loc[8, "mom_growth_pct"] == pytest.approx(expected, abs=0.06)


def test_a_category_without_sales_in_a_month_keeps_its_row_in_the_comparison(database, results):
    full = results["15_month_over_month_comparison"].reset_index(drop=True)
    category, gap = full.loc[len(full) // 2, ["category_name", "month"]]
    delete_lines = """
        DELETE FROM order_items WHERE order_id IN (
            SELECT order_id FROM orders WHERE date_trunc('month', order_date)::date = :month
        ) AND product_id IN (
            SELECT p.product_id FROM products p JOIN categories c USING (category_id)
            WHERE c.category_name = :category
        )
    """
    compared = run_after_deleting_lines(
        database,
        "15_month_over_month_comparison.sql",
        delete_lines,
        {"month": gap, "category": category},
    )

    assert len(compared) == len(full)
    row = compared[(compared["category_name"] == category) & (compared["month"] == gap)].iloc[0]
    assert row["revenue"] == 0
    assert row["mom_change_pct"] == -100


def test_customer_ranking_is_sorted_and_cumulative_share_ends_below_100(results):
    top = results["04_top_customers"]
    assert top["revenue"].is_monotonic_decreasing
    assert top["cumulative_share_pct"].is_monotonic_increasing
    assert top["cumulative_share_pct"].iloc[-1] <= 100


def test_twelve_month_figures_use_calendar_months_back_from_the_last_sale(results, lines, cleaned):
    names = cleaned.clean["categories"].set_index("category_id")["category_name"]
    last_day = lines["order_date"].max()
    recent = lines[lines["order_date"] > last_day - pd.DateOffset(months=12)]
    category = recent["category_id"].map(names)

    revenue = recent.groupby(category)["revenue"].sum().round(2).to_dict()
    categories = results["05_category_performance"].set_index("category_name")
    assert categories["revenue_last_12m"].astype(float).round(2).to_dict() == pytest.approx(revenue)

    cost = (recent["quantity"] * recent["cost_price"]).round(2).groupby(category).sum()
    turnover = results["09_inventory_turnover"].set_index("category_name")["cogs_12m"]
    turnover = turnover.drop("All categories").astype(float).round(2)
    assert turnover.to_dict() == pytest.approx(cost[turnover.index].round(2).to_dict())


def test_category_shares_add_up_to_100(results, lines):
    categories = results["05_category_performance"]
    assert categories["revenue"].sum() == pytest.approx(lines["revenue"].sum(), rel=1e-6)
    assert categories["share_pct"].sum() == pytest.approx(100, abs=0.5)
    assert set(categories["trend"]) <= {"Declining", "Gaining share", "Losing share", "Steady"}


def test_order_value_by_customer_type_adds_up_to_the_total_row(results, lines):
    table = results["07_average_order_value"].set_index("customer_type")
    total = table.loc["All customers"]
    orders = lines["order_id"].nunique()
    assert total["orders"] == orders
    assert table.drop(index="All customers")["orders"].sum() == orders
    assert total["avg_order_value"] == pytest.approx(lines["revenue"].sum() / orders, abs=0.01)


def test_repeat_customers_by_type_add_up_to_the_total_row(results, lines):
    table = results["08_repeat_customers"].set_index("customer_type")
    total = table.loc["All customers"]
    parts = table.drop(index="All customers")
    orders_per_customer = lines.groupby("customer_id")["order_id"].nunique()
    assert total["customers"] == len(orders_per_customer)
    assert total["repeat_customers"] == (orders_per_customer >= 2).sum()
    assert parts["customers"].sum() == total["customers"]
    assert parts["repeat_customers"].sum() == total["repeat_customers"]


def test_customer_segments_cover_every_buying_customer_once(results, lines):
    segments = results["13_customer_segmentation"]
    assert segments["customers"].sum() == lines["customer_id"].nunique()
    assert segments["revenue_share_pct"].sum() == pytest.approx(100, abs=0.5)


def test_regional_revenue_adds_up_to_the_total(results, lines):
    regions = results["12_regional_performance"]
    assert regions["revenue"].sum() == pytest.approx(lines["revenue"].sum(), rel=1e-6)
    assert regions["revenue_share_pct"].sum() == pytest.approx(100, abs=0.5)


def test_order_status_mix_counts_every_order(results, cleaned):
    mix = results["17_order_status_mix"].set_index("location_name")
    orders = cleaned.clean["orders"]
    total = mix.loc["All locations"]
    assert total["orders"] == len(orders)
    assert total["cancelled"] == (orders["order_status"] == "Cancelled").sum()
    assert total["returned"] == (orders["order_status"] == "Returned").sum()
    assert mix.drop(index="All locations")["orders"].sum() == len(orders)
