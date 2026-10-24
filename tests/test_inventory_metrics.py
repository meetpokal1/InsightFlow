"""Unit tests for inventory metrics semantics and capital replenishment calculations."""

import numpy as np
import pandas as pd
import pytest

from src.analytics.demo import build_inventory_view, build_sales_lines, inventory_summary


def test_inventory_synthetic_boundary_cases():
    """Verify inventory metrics under exact synthetic boundary scenarios."""
    df = pd.DataFrame(
        [
            # Position 1: Zero stock (stockout)
            {
                "quantity_on_hand": 0,
                "reorder_level": 50,
                "cost_price": 100.0,
                "selling_price": 150.0,
                "suggested_order_qty": 60,
                "inventory_value": 0.0,
            },
            # Position 2: Exactly at reorder level (low stock, replenishment 0)
            {
                "quantity_on_hand": 50,
                "reorder_level": 50,
                "cost_price": 200.0,
                "selling_price": 300.0,
                "suggested_order_qty": 20,
                "inventory_value": 10000.0,
            },
            # Position 3: Above reorder level (healthy, replenishment 0)
            {
                "quantity_on_hand": 120,
                "reorder_level": 50,
                "cost_price": 50.0,
                "selling_price": 80.0,
                "suggested_order_qty": 0,
                "inventory_value": 6000.0,
            },
            # Position 4: Partial buffer deficit
            {
                "quantity_on_hand": 20,
                "reorder_level": 50,
                "cost_price": 10.0,
                "selling_price": 25.0,
                "suggested_order_qty": 45,
                "inventory_value": 200.0,
            },
            # Position 5: Negative quantity edge case (clamped by max(0, reorder - on_hand))
            {
                "quantity_on_hand": -5,
                "reorder_level": 10,
                "cost_price": 40.0,
                "selling_price": 60.0,
                "suggested_order_qty": 25,
                "inventory_value": -200.0,
            },
        ]
    )

    df["replenishment_qty_required"] = np.maximum(
        0, df["reorder_level"] - np.maximum(0, df["quantity_on_hand"])
    ).astype(int)
    df["replenishment_cost_estimate"] = (df["replenishment_qty_required"] * df["cost_price"]).round(
        2
    )
    df["stock_gap_retail_val"] = (df["replenishment_qty_required"] * df["selling_price"]).round(2)

    # Position 1: 0 stock, reorder 50 -> required 50
    assert df.loc[0, "replenishment_qty_required"] == 50
    assert df.loc[0, "replenishment_cost_estimate"] == 5000.0
    assert df.loc[0, "stock_gap_retail_val"] == 7500.0

    # Position 2: at reorder level -> required 0
    assert df.loc[1, "replenishment_qty_required"] == 0
    assert df.loc[1, "replenishment_cost_estimate"] == 0.0
    assert df.loc[1, "stock_gap_retail_val"] == 0.0

    # Position 3: above reorder level -> required 0
    assert df.loc[2, "replenishment_qty_required"] == 0
    assert df.loc[2, "replenishment_cost_estimate"] == 0.0
    assert df.loc[2, "stock_gap_retail_val"] == 0.0

    # Position 4: 20 on hand, reorder 50 -> required 30
    assert df.loc[3, "replenishment_qty_required"] == 30
    assert df.loc[3, "replenishment_cost_estimate"] == 300.0
    assert df.loc[3, "stock_gap_retail_val"] == 750.0

    # Position 5: negative on hand clamped to 0 -> required 10
    assert df.loc[4, "replenishment_qty_required"] == 10


def test_build_inventory_view_and_summary_on_cleaned_dataset(cleaned):
    """Test inventory view and summary semantics against the fixture dataset."""
    lines = build_sales_lines(cleaned.clean)
    inventory = build_inventory_view(cleaned.clean, lines)

    # Verify column presence
    expected_cols = {
        "replenishment_qty_required",
        "replenishment_cost_estimate",
        "stock_gap_retail_val",
        "is_stockout",
        "is_below_reorder",
        "suggested_order_qty",
        "inventory_value",
    }
    assert expected_cols.issubset(inventory.columns)

    # Verify semantic relationships
    assert (inventory["replenishment_qty_required"] >= 0).all()
    assert (inventory["replenishment_cost_estimate"] >= 0).all()
    assert (inventory["stock_gap_retail_val"] >= 0).all()
    assert (
        inventory["replenishment_cost_estimate"] <= inventory["stock_gap_retail_val"] + 1e-5
    ).all()

    # Verify summary aggregations
    summary = inventory_summary(inventory)
    assert summary["total_positions"] == len(cleaned.clean["inventory"])
    assert summary["stockout_positions"] == int(inventory["quantity_on_hand"].eq(0).sum())
    assert summary["below_reorder_positions"] == int(
        (inventory["quantity_on_hand"] < inventory["reorder_level"]).sum()
    )
    assert summary["replenishment_units_required"] == int(
        inventory["replenishment_qty_required"].sum()
    )
    assert summary["replenishment_cost_estimate"] == pytest.approx(
        float(inventory["replenishment_cost_estimate"].sum()), abs=0.01
    )
    assert summary["stock_gap_retail_val"] == pytest.approx(
        float(inventory["stock_gap_retail_val"].sum()), abs=0.01
    )


def test_production_clean_inventory_metrics():
    """Verify inventory metrics match the documented baseline on production clean CSVs."""
    import pathlib

    data_dir = pathlib.Path(__file__).resolve().parent.parent / "data" / "processed"
    if not (data_dir / "inventory.csv").exists():
        pytest.skip("Production clean data files not found in data/processed.")

    clean_tables = {f.stem: pd.read_csv(f) for f in data_dir.glob("*.csv")}
    lines = build_sales_lines(clean_tables)
    inventory = build_inventory_view(clean_tables, lines)

    summary = inventory_summary(inventory)
    assert summary["total_positions"] == 449
    assert summary["stockout_positions"] == 40
    assert summary["below_reorder_positions"] == 96
    assert summary["replenishment_units_required"] == 5791
    assert summary["replenishment_cost_estimate"] == pytest.approx(966026.68, abs=0.1)
    assert summary["stock_gap_retail_val"] == pytest.approx(1340814.00, abs=0.1)
    assert summary["total_inventory_value"] == pytest.approx(22493991.10, abs=1.0)


def test_inventory_summary_empty_dataframe():
    """Verify inventory summary behaves cleanly with empty input."""
    empty_df = pd.DataFrame()
    summary = inventory_summary(empty_df)
    assert summary["total_positions"] == 0
    assert summary["total_inventory_value"] == 0.0
    assert summary["stockout_positions"] == 0
    assert summary["below_reorder_positions"] == 0
    assert summary["replenishment_units_required"] == 0
    assert summary["replenishment_cost_estimate"] == 0.0
    assert summary["stock_gap_retail_val"] == 0.0
