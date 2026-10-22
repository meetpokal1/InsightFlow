"""The API endpoints. Numbers are compared with an independent calculation in pandas."""

import math

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from api.main import create_app
from tests.helpers import completed_sales_lines

DATA_ENDPOINTS = [
    "/sales/summary",
    "/sales/monthly",
    "/products/top",
    "/inventory/low-stock",
    "/customers/top",
    "/analytics/category-performance",
]


@pytest.fixture(scope="module")
def client(database):
    with TestClient(create_app(engine=database)) as client:
        yield client


@pytest.fixture(scope="module")
def lines(cleaned):
    return completed_sales_lines(cleaned.clean)


# no database needed for this one


def test_a_database_outage_gives_503_and_a_clear_message():
    engine = create_engine(
        "postgresql+psycopg2://nobody:secret@localhost:1/none", connect_args={"connect_timeout": 1}
    )
    with TestClient(create_app(engine=engine)) as client:
        for url in ["/health", *DATA_ENDPOINTS]:
            response = client.get(url)
            assert response.status_code == 503, url
            assert response.json() == {"detail": "The database is not available"}


# everything below needs the test database

db = pytest.mark.db


@db
def test_health_checks_the_database(client):
    assert client.get("/health").json() == {"status": "ok"}


@db
def test_all_endpoints_are_in_the_swagger_document(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert set(DATA_ENDPOINTS) <= set(paths)
    assert client.get("/docs").status_code == 200


# GET /sales/summary


@db
def test_sales_summary_matches_pandas(client, lines):
    body = client.get("/sales/summary").json()
    assert body["total_revenue"] == pytest.approx(lines["revenue"].sum(), rel=1e-6)
    assert body["total_profit"] == pytest.approx(lines["profit"].sum(), rel=1e-6)
    assert body["total_orders"] == lines["order_id"].nunique()
    assert body["total_customers"] == lines["customer_id"].nunique()
    assert body["units_sold"] == lines["quantity"].sum()
    assert body["avg_order_value"] == pytest.approx(
        lines["revenue"].sum() / lines["order_id"].nunique(), abs=0.01
    )
    assert body["margin_pct"] == pytest.approx(
        100 * lines["profit"].sum() / lines["revenue"].sum(), abs=0.1
    )


@db
def test_sales_summary_filters_by_dates_and_location(client, lines):
    params = {"start_date": "2026-01-01", "end_date": "2026-03-31", "location_id": "L01"}
    window = lines[
        (lines["order_date"] >= "2026-01-01")
        & (lines["order_date"] <= "2026-03-31")
        & (lines["location_id"] == "L01")
    ]
    assert len(window) > 0
    body = client.get("/sales/summary", params=params).json()
    assert body["total_orders"] == window["order_id"].nunique()
    assert body["total_revenue"] == pytest.approx(window["revenue"].sum(), rel=1e-6)


@db
def test_a_one_day_range_includes_both_ends(client, lines):
    day = lines["order_date"].iloc[len(lines) // 2]
    one_day = lines[lines["order_date"] == day]
    params = {"start_date": day.date().isoformat(), "end_date": day.date().isoformat()}
    body = client.get("/sales/summary", params=params).json()
    assert body["total_orders"] == one_day["order_id"].nunique() > 0
    assert body["total_revenue"] == pytest.approx(one_day["revenue"].sum(), rel=1e-6)


@db
def test_a_period_without_sales_gives_zeros_not_an_error(client):
    body = client.get("/sales/summary", params={"start_date": "2030-01-01"}).json()
    assert body["total_orders"] == 0
    assert body["total_revenue"] == 0
    assert body["margin_pct"] is None
    assert body["avg_order_value"] is None


@db
def test_inventory_value_is_not_affected_by_the_date_filter(client):
    everything = client.get("/sales/summary").json()["inventory_value"]
    one_day = client.get(
        "/sales/summary", params={"start_date": "2026-01-01", "end_date": "2026-01-02"}
    )
    assert one_day.json()["inventory_value"] == everything > 0


# GET /sales/monthly


@db
def test_monthly_sales_add_up_to_the_total_and_growth_is_month_on_month(client, lines):
    months = client.get("/sales/monthly").json()
    assert [row["month"] for row in months] == sorted(row["month"] for row in months)
    assert sum(row["revenue"] for row in months) == pytest.approx(lines["revenue"].sum(), rel=1e-6)
    assert sum(row["orders"] for row in months) == lines["order_id"].nunique()
    assert months[0]["mom_growth_pct"] is None
    expected = 100 * (months[1]["revenue"] / months[0]["revenue"] - 1)
    assert months[1]["mom_growth_pct"] == pytest.approx(expected, abs=0.06)


@db
def test_monthly_sales_respect_the_date_range(client):
    months = client.get("/sales/monthly", params={"start_date": "2026-07-01"}).json()
    assert [row["month"] for row in months] == ["2026-07-01", "2026-08-01", "2026-09-01"]


# GET /products/top


@db
@pytest.mark.parametrize(
    "metric, column", [("revenue", "revenue"), ("profit", "profit"), ("units", "quantity")]
)
def test_top_products_are_ranked_by_the_chosen_metric(client, lines, metric, column):
    body = client.get("/products/top", params={"metric": metric, "limit": 5}).json()
    totals = lines.groupby("product_id")[column].sum().reset_index()
    expected = totals.sort_values([column, "product_id"], ascending=[False, True]).head(5)
    assert [row["product_id"] for row in body] == expected["product_id"].tolist()
    assert [row["rank"] for row in body] == [1, 2, 3, 4, 5]


@db
def test_top_products_can_be_limited_to_one_category(client, cleaned):
    category = cleaned.clean["categories"]["category_id"].iloc[0]
    in_category = set(cleaned.clean["products"].query("category_id == @category")["product_id"])
    body = client.get("/products/top", params={"category_id": category, "limit": 100}).json()
    assert body
    assert {row["product_id"] for row in body} <= in_category


@db
def test_top_products_default_to_ten_by_revenue(client):
    body = client.get("/products/top").json()
    revenues = [row["revenue"] for row in body]
    assert len(body) == 10
    assert revenues == sorted(revenues, reverse=True)


# GET /inventory/low-stock


@db
def test_low_stock_lists_the_most_urgent_items_first(client):
    body = client.get("/inventory/low-stock", params={"limit": 500}).json()
    order = {"Out of stock": 1, "Stock-out risk": 2, "Low stock": 3}
    assert body
    assert {row["stock_status"] for row in body} <= set(order)
    priorities = [order[row["stock_status"]] for row in body]
    assert priorities == sorted(priorities)
    assert all(row["suggested_order_qty"] >= 0 for row in body)


@db
def test_low_stock_can_be_filtered_by_status_and_location(client):
    only_empty = client.get("/inventory/low-stock", params={"status": "Out of stock"}).json()
    assert only_empty
    assert {row["stock_status"] for row in only_empty} == {"Out of stock"}
    assert all(row["quantity_on_hand"] == 0 for row in only_empty)

    at_l01 = client.get("/inventory/low-stock", params={"location_id": "L01"}).json()
    assert at_l01
    assert {row["location_id"] for row in at_l01} == {"L01"}


@db
def test_out_of_stock_list_matches_pandas(client, cleaned, lines):
    inventory = cleaned.clean["inventory"]
    snapshot = inventory["snapshot_date"].max()
    recent = lines[lines["order_date"] > snapshot - pd.Timedelta(days=90)]
    sold = recent.groupby(["product_id", "location_id"])["quantity"].sum()
    empty = inventory[inventory["quantity_on_hand"] == 0]
    expected = {
        (row.product_id, row.location_id)
        for row in empty.itertuples()
        if sold.get((row.product_id, row.location_id), 0) > 0
    }
    body = client.get("/inventory/low-stock", params={"status": "Out of stock", "limit": 500})
    assert expected
    assert {(row["product_id"], row["location_id"]) for row in body.json()} == expected


@db
def test_suggested_order_covers_the_lead_time_plus_30_days(client):
    body = client.get("/inventory/low-stock", params={"status": "Out of stock"}).json()
    assert body
    for row in body:
        needed = row["avg_daily_units"] * (row["lead_time_days"] + 30)
        assert row["suggested_order_qty"] == math.ceil(round(needed, 6))  # nothing is on hand


# GET /customers/top


@db
def test_top_customers_match_pandas(client, lines):
    body = client.get("/customers/top", params={"limit": 5}).json()
    totals = lines.groupby("customer_id")["revenue"].sum().reset_index()
    expected = totals.sort_values(["revenue", "customer_id"], ascending=[False, True]).head(5)
    assert [row["customer_id"] for row in body] == expected["customer_id"].tolist()
    assert body[0]["revenue"] == pytest.approx(expected["revenue"].iloc[0], rel=1e-6)
    share = 100 * expected["revenue"].iloc[0] / lines["revenue"].sum()
    assert body[0]["revenue_share_pct"] == pytest.approx(share, abs=0.01)
    assert (
        body[0]["orders"]
        == lines[lines["customer_id"] == body[0]["customer_id"]]["order_id"].nunique()
    )


# GET /analytics/category-performance


@db
def test_category_performance_covers_all_revenue(client, lines):
    body = client.get("/analytics/category-performance").json()
    assert sum(row["revenue"] for row in body) == pytest.approx(lines["revenue"].sum(), rel=1e-6)
    assert sum(row["share_pct"] for row in body) == pytest.approx(100, abs=0.5)
    assert {row["trend"] for row in body} <= {
        "Declining",
        "Gaining share",
        "Losing share",
        "Steady",
    }


# bad requests


@db
@pytest.mark.parametrize(
    "url, status",
    [
        ("/products/top?limit=0", 422),
        ("/products/top?limit=101", 422),
        ("/products/top?metric=weight", 422),
        ("/customers/top?limit=-1", 422),
        ("/sales/summary?start_date=yesterday", 422),
        ("/sales/monthly?end_date=2026-13-45", 422),
        ("/sales/summary?start_date=2026-05-01&end_date=2026-01-01", 422),
        ("/inventory/low-stock?status=Healthy", 422),
        ("/inventory/low-stock?limit=0", 422),
        ("/sales/summary?location_id=L99", 404),
        ("/sales/monthly?location_id=L99", 404),
        ("/inventory/low-stock?location_id=L99", 404),
        ("/products/top?category_id=NOPE", 404),
        ("/sales/summary?location_id=L01'%20OR%20'1'='1", 404),
        ("/no-such-endpoint", 404),
    ],
)
def test_bad_requests_get_a_clear_error_and_never_a_server_error(client, url, status):
    response = client.get(url)
    assert response.status_code == status
    assert "detail" in response.json()
