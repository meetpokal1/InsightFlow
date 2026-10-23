"""Unit tests for the Price and Margin Sensitivity Simulator."""

import pandas as pd
import pytest

from src.analytics.demo import build_sales_lines, simulate_price_sensitivity


def test_basmati_rice_case_study_sensitivity():
    """Verify the exact case study figures for Basmati Rice 5kg (P0010)."""
    import pathlib

    data_dir = pathlib.Path(__file__).resolve().parent.parent / "data" / "processed"
    if not (data_dir / "products.csv").exists():
        pytest.skip("Processed data not available.")

    clean_tables = {f.stem: pd.read_csv(f) for f in data_dir.glob("*.csv")}
    sales_lines = build_sales_lines(clean_tables)

    # 1. Baseline verification
    res_base = simulate_price_sensitivity(
        sales_lines, product_id="P0010", price_change_pct=0.0, volume_change_pct=0.0
    )
    assert res_base["baseline"]["units"] == 23563
    assert res_base["baseline"]["revenue"] == pytest.approx(16471108.80, abs=0.02)
    assert res_base["baseline"]["cogs"] == pytest.approx(16117092.00, abs=0.02)
    assert res_base["baseline"]["gross_profit"] == pytest.approx(354016.80, abs=0.02)
    assert res_base["baseline"]["margin_pct"] == pytest.approx(2.15, abs=0.02)

    # 2. Scenario A: +3% price, 0% volume change (pure price increase)
    res_a = simulate_price_sensitivity(
        sales_lines, product_id="P0010", price_change_pct=3.0, volume_change_pct=0.0
    )
    assert res_a["modeled"]["revenue"] == pytest.approx(16965242.06, abs=0.05)
    assert res_a["modeled"]["cogs"] == pytest.approx(16117092.00, abs=0.05)
    assert res_a["modeled"]["gross_profit"] == pytest.approx(848150.06, abs=0.05)
    assert res_a["delta"]["gross_profit"] == pytest.approx(494133.26, abs=0.05)

    # 3. Scenario B: +3% price, -4.5% volume change (assumed elasticity |e|=1.5)
    res_b = simulate_price_sensitivity(
        sales_lines, product_id="P0010", price_change_pct=3.0, volume_change_pct=-4.5
    )
    assert res_b["modeled"]["revenue"] == pytest.approx(16201806.17, abs=0.05)
    assert res_b["modeled"]["cogs"] == pytest.approx(15391822.86, abs=0.05)
    assert res_b["modeled"]["gross_profit"] == pytest.approx(809983.31, abs=0.05)
    assert res_b["modeled"]["margin_pct"] == pytest.approx(5.00, abs=0.02)
    assert res_b["delta"]["gross_profit"] == pytest.approx(455966.51, abs=0.05)
    assert res_b["delta"]["margin_points"] == pytest.approx(2.85, abs=0.02)

    # 4. Break-even volume decline verification: ~58.26%
    assert res_b["break_even_volume_decline_pct"] == pytest.approx(58.26, abs=0.05)

    # 5. Same result using elasticity parameter
    res_b_elasticity = simulate_price_sensitivity(
        sales_lines, product_id="P0010", price_change_pct=3.0, elasticity=1.5
    )
    assert res_b_elasticity["volume_change_pct"] == pytest.approx(-4.5, abs=0.01)
    assert res_b_elasticity["modeled"]["gross_profit"] == pytest.approx(
        res_b["modeled"]["gross_profit"], abs=0.05
    )


def test_wireless_mouse_sensitivity():
    """Verify simulation for Wireless Mouse (P0055)."""
    import pathlib

    data_dir = pathlib.Path(__file__).resolve().parent.parent / "data" / "processed"
    if not (data_dir / "products.csv").exists():
        pytest.skip("Processed data not available.")

    clean_tables = {f.stem: pd.read_csv(f) for f in data_dir.glob("*.csv")}
    sales_lines = build_sales_lines(clean_tables)

    res = simulate_price_sensitivity(
        sales_lines, product_id="P0055", price_change_pct=5.0, volume_change_pct=-2.0
    )
    assert res["baseline"]["units"] == 15725
    assert res["baseline"]["revenue"] == pytest.approx(11520836.93, abs=0.05)
    assert res["baseline"]["margin_pct"] == pytest.approx(25.84, abs=0.05)
    assert res["delta"]["gross_profit"] > 0


def test_sensitivity_error_handling():
    """Verify invalid product id raises ValueError."""
    dummy_df = pd.DataFrame(
        [
            {
                "product_id": "P0001",
                "product_name": "Test",
                "category_name": "Cat",
                "quantity": 10,
                "net_revenue": 100.0,
                "cost_price": 5.0,
            }
        ]
    )
    with pytest.raises(ValueError, match="not found"):
        simulate_price_sensitivity(dummy_df, product_id="P9999", price_change_pct=5.0)
