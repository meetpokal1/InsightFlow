"""Checks for the no-database dashboard calculations."""

import pandas as pd
import pytest

from src.analytics.demo import (
    build_customer_summary,
    build_inventory_view,
    build_sales_lines,
    format_inr,
    monthly_sales,
    sales_summary,
)


def test_sales_lines_only_include_completed_orders_and_match_documented_formulas(cleaned):
    lines = build_sales_lines(cleaned.clean)
    assert not lines.empty
    assert set(lines["order_status"]) == {"Completed"}
    row = lines.iloc[0]
    expected_revenue = round(row.quantity * row.unit_price * (1 - row.discount_pct / 100), 2)
    expected_profit = round(
        row.quantity * row.unit_price * (1 - row.discount_pct / 100)
        - row.quantity * row.cost_price,
        2,
    )
    assert row.net_revenue == pytest.approx(expected_revenue)
    assert row.gross_profit == pytest.approx(expected_profit)


def test_monthly_revenue_rolls_up_to_filtered_total(cleaned):
    lines = build_sales_lines(cleaned.clean)
    monthly = monthly_sales(lines)
    assert monthly["revenue"].sum() == pytest.approx(lines["net_revenue"].sum(), abs=0.02)
    assert monthly["gross_profit"].sum() == pytest.approx(lines["gross_profit"].sum(), abs=0.02)
    first_growth = monthly.iloc[0]["mom_growth_pct"]
    assert pd.isna(first_growth)  # no prior month


def test_summary_calculates_distinct_order_and_customer_counts(cleaned):
    lines = build_sales_lines(cleaned.clean)
    summary = sales_summary(lines)
    assert summary["orders"] == lines["order_id"].nunique()
    assert summary["customers"] == lines["customer_id"].nunique()
    assert summary["revenue"] == pytest.approx(lines["net_revenue"].sum())
    assert summary["average_order_value"] == pytest.approx(summary["revenue"] / summary["orders"])


def test_inventory_view_preserves_snapshot_positions_and_valid_statuses(cleaned):
    lines = build_sales_lines(cleaned.clean)
    inventory = build_inventory_view(cleaned.clean, lines)
    assert len(inventory) == len(cleaned.clean["inventory"])
    assert inventory["stock_status"].notna().all()
    assert inventory["suggested_order_qty"].ge(0).all()
    assert inventory["inventory_value"].ge(0).all()


def test_customer_summary_keeps_customers_without_completed_orders(cleaned):
    lines = build_sales_lines(cleaned.clean)
    summary = build_customer_summary(lines, cleaned.clean["customers"])
    assert len(summary) == len(cleaned.clean["customers"])
    assert summary["customer_id"].is_unique
    assert (summary["orders"] == 0).any()


def test_inr_format_uses_compact_indian_units():
    assert format_inr(1_250_000) == "₹12.50 L"
    assert format_inr(12_500_000) == "₹1.25 Cr"
    assert format_inr(None) == "—"


def test_dashboard_bundle_carries_the_pipeline_quality_report_and_profile(cleaned):
    from src.analytics.demo import build_dashboard_data

    data = build_dashboard_data(
        cleaned.clean,
        quality_log=cleaned.quality_log,
        raw_profile=cleaned.profile,
    )
    assert len(data["sales_lines"]) > 0
    assert not data["quality_log"].empty
    assert not data["raw_profile"].empty
    assert len(data["inventory"]) == len(cleaned.clean["inventory"])
