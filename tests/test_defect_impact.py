"""Unit tests for the data defect to business decision impact analysis."""

import pandas as pd

from src.analytics.defect_impact import (
    build_defect_traceability_matrix,
    compute_customer_defect_impact,
    compute_inventory_defect_impact,
    compute_sales_defect_impact,
    generate_defect_impact_report,
)
from src.analytics.demo import build_inventory_view, build_sales_lines, sales_summary


def test_compute_sales_defect_impact_with_cleaned_fixture(cleaned):
    """Verify sales distortion metrics calculated against the small test fixture."""
    clean_lines = build_sales_lines(cleaned.clean)
    sales_sum = sales_summary(clean_lines)

    df = compute_sales_defect_impact(cleaned.raw["orders"], cleaned.raw["order_items"], sales_sum)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert set(df["Metric"]) == {"Net Sales Turnover", "Fulfilled Order Volume", "Units Sold"}

    turnover_row = df.loc[df["Metric"] == "Net Sales Turnover"].iloc[0]
    assert "₹" in turnover_row["Validated Ground Truth"]
    assert "Isolated" in turnover_row["Pipeline Control & Root Cause"]


def test_compute_customer_defect_impact_with_cleaned_fixture(cleaned):
    """Verify customer fragmentation and ghost account consolidation logic."""
    clean_lines = build_sales_lines(cleaned.clean)

    res = compute_customer_defect_impact(
        cleaned.raw["customers"],
        cleaned.raw["orders"],
        cleaned.clean["customers"],
        clean_lines,
    )
    assert isinstance(res, dict)
    assert "summary" in res
    assert "top_fragmented" in res
    assert "orders_remapped" in res
    assert isinstance(res["orders_remapped"], int)
    assert res["orders_remapped"] >= 0
    assert isinstance(res["ghost_revenue"], float)
    assert res["ghost_revenue"] >= 0.0

    summary_df = res["summary"]
    assert len(summary_df) == 3
    assert "Active Buying Accounts" in summary_df["Dimension"].values


def test_compute_inventory_defect_impact_with_cleaned_fixture(cleaned):
    """Verify inventory threshold coverage and stockout prevention reporting."""
    clean_lines = build_sales_lines(cleaned.clean)
    inventory_view = build_inventory_view(cleaned.clean, clean_lines)

    df = compute_inventory_defect_impact(cleaned.raw["inventory"], inventory_view)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert "Replenishment Threshold Coverage" in df["Inventory Health Metric"].values

    coverage_row = df.loc[df["Inventory Health Metric"] == "Replenishment Threshold Coverage"].iloc[
        0
    ]
    assert coverage_row["Validated Pipeline"] == "100.0% (0 NULL)"


def test_build_defect_traceability_matrix(cleaned):
    """Verify that all 7 major defect clusters are documented in the traceability matrix."""
    matrix = build_defect_traceability_matrix(cleaned.quality_log)
    assert isinstance(matrix, pd.DataFrame)
    assert len(matrix) >= 7

    categories = set(matrix["Defect Category"])
    assert "Severe Quantity Outliers" in categories
    assert "Misplaced Price Decimals" in categories
    assert "Inverted Cost/Price Pairs" in categories
    assert "Split Customer Identity" in categories
    assert "Header vs Line Discrepancies" in categories
    assert "Missing Reorder Levels" in categories
    assert "Exact Duplicate Records" in categories

    for col in [
        "Pipeline Control",
        "Downstream Metric at Risk",
        "Unvalidated Business Consequence",
    ]:
        assert (matrix[col].str.len() > 0).all()


def test_generate_defect_impact_report_integration(cleaned):
    """Verify the full report bundle generated from pipeline results."""
    clean_lines = build_sales_lines(cleaned.clean)
    inventory_view = build_inventory_view(cleaned.clean, clean_lines)

    report = generate_defect_impact_report(
        cleaned.raw,
        cleaned.clean,
        clean_lines,
        inventory_view,
        cleaned.quality_log,
    )
    assert isinstance(report, dict)
    expected_keys = {
        "sales_impact",
        "customer_impact",
        "customer_top_fragmented",
        "inventory_impact",
        "traceability_matrix",
        "metrics",
    }
    assert expected_keys.issubset(report.keys())
    assert not report["sales_impact"].empty
    assert not report["customer_impact"].empty
    assert not report["inventory_impact"].empty
    assert not report["traceability_matrix"].empty


def test_defect_impact_edge_case_empty_data():
    """Verify graceful handling with minimal / empty dataframes."""
    empty_orders = pd.DataFrame(columns=["order_id", "customer_id", "order_status", "order_total"])
    empty_items = pd.DataFrame(columns=["order_id", "quantity", "unit_price", "discount_pct"])
    sales_metrics = {"revenue": 0.0, "orders": 0, "units_sold": 0}

    df = compute_sales_defect_impact(empty_orders, empty_items, sales_metrics)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
