"""Pandas calculations used by the no-database InsightFlow demo dashboard.

The dashboard uses the same cleaned synthetic inputs as the PostgreSQL pipeline. The
SQL views remain the canonical implementation for the full database/API stack; these
pandas functions make the interactive demo usable without PostgreSQL credentials.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def build_sales_lines(clean: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build completed-order lines with the metrics used by the SQL sales fact view."""
    orders = clean["orders"].copy()
    orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
    orders = orders.loc[orders["order_status"].eq("Completed")]

    products = clean["products"].copy()
    customers = clean["customers"][["customer_id", "customer_name", "customer_type", "city"]]
    locations = clean["locations"][["location_id", "location_name", "region", "state"]]
    categories = clean["categories"]

    lines = clean["order_items"].merge(orders, on="order_id", how="inner", validate="many_to_one")
    lines = lines.merge(products, on="product_id", how="inner", validate="many_to_one")
    lines = lines.merge(categories, on="category_id", how="left", validate="many_to_one")
    lines = lines.merge(customers, on="customer_id", how="inner", validate="many_to_one")
    lines = lines.merge(locations, on="location_id", how="inner", validate="many_to_one")

    extended_price = lines["quantity"] * lines["unit_price"] * (1 - lines["discount_pct"] / 100)
    extended_cost = lines["quantity"] * lines["cost_price"]
    lines["net_revenue"] = extended_price.round(2)
    lines["cost_of_goods"] = extended_cost.round(2)
    lines["gross_profit"] = (extended_price - extended_cost).round(2)
    return lines


def build_inventory_view(
    clean: dict[str, pd.DataFrame], sales_lines: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Apply the inventory status and suggested-order rules documented in SQL views."""
    sales_lines = sales_lines if sales_lines is not None else build_sales_lines(clean)
    inventory = clean["inventory"].copy()
    inventory["snapshot_date"] = pd.to_datetime(inventory["snapshot_date"], errors="coerce")
    snapshot_date = inventory["snapshot_date"].max()

    recent_sales = sales_lines.loc[
        sales_lines["order_date"] > snapshot_date - pd.Timedelta(days=90)
    ]
    sold = (
        recent_sales.groupby(["product_id", "location_id"], as_index=False)["quantity"]
        .sum()
        .rename(columns={"quantity": "units_sold_90d"})
    )

    products = clean["products"]
    suppliers = clean["suppliers"][["supplier_id", "supplier_name", "lead_time_days"]]
    locations = clean["locations"][["location_id", "location_name", "region", "state"]]
    categories = clean["categories"]
    view = inventory.merge(products, on="product_id", how="inner", validate="many_to_one")
    view = view.merge(suppliers, on="supplier_id", how="inner", validate="many_to_one")
    view = view.merge(locations, on="location_id", how="inner", validate="many_to_one")
    view = view.merge(categories, on="category_id", how="left", validate="many_to_one")
    view = view.merge(sold, on=["product_id", "location_id"], how="left", validate="one_to_one")

    view["units_sold_90d"] = view["units_sold_90d"].fillna(0).astype(int)
    view["avg_daily_units"] = (view["units_sold_90d"] / 90.0).round(2)
    view["inventory_value"] = (view["quantity_on_hand"] * view["cost_price"]).round(2)
    has_sales = view["units_sold_90d"].gt(0)
    view["days_of_cover"] = np.where(
        has_sales,
        (view["quantity_on_hand"] * 90.0 / view["units_sold_90d"]).round(1),
        np.nan,
    )

    lead_time = view["lead_time_days"]
    on_hand = view["quantity_on_hand"]
    days_cover = view["days_of_cover"]
    view["stock_status"] = np.select(
        [
            ~has_sales,
            has_sales & on_hand.eq(0),
            has_sales & on_hand.gt(0) & (days_cover < lead_time),
            has_sales
            & on_hand.gt(0)
            & (days_cover >= lead_time)
            & on_hand.le(view["reorder_level"]),
            has_sales
            & on_hand.gt(0)
            & (days_cover >= lead_time)
            & on_hand.gt(view["reorder_level"])
            & (days_cover > 180),
        ],
        ["No recent sales", "Out of stock", "Stock-out risk", "Low stock", "Overstocked"],
        default="Healthy",
    )
    projected_need = np.ceil(view["avg_daily_units"] * (lead_time + 30)) - on_hand
    view["suggested_order_qty"] = np.maximum(projected_need, 0).astype(int)

    # Replenishment requirements and stock gap valuations
    view["replenishment_qty_required"] = np.maximum(
        0, view["reorder_level"] - view["quantity_on_hand"]
    ).astype(int)
    view["replenishment_cost_estimate"] = (
        view["replenishment_qty_required"] * view["cost_price"]
    ).round(2)
    view["stock_gap_retail_val"] = (
        view["replenishment_qty_required"] * view["selling_price"]
    ).round(2)
    view["is_stockout"] = view["quantity_on_hand"].eq(0)
    view["is_below_reorder"] = view["quantity_on_hand"].lt(view["reorder_level"])
    return view


def build_customer_summary(sales_lines: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
    """Summarize completed-order activity for every customer, including non-buyers."""
    facts = sales_lines.groupby(
        ["customer_id", "customer_name", "customer_type", "city"], as_index=False
    ).agg(
        revenue=("net_revenue", "sum"),
        gross_profit=("gross_profit", "sum"),
        orders=("order_id", "nunique"),
        last_order_date=("order_date", "max"),
    )
    all_customers = customers[["customer_id", "customer_name", "customer_type", "city"]]
    summary = all_customers.merge(
        facts,
        on=["customer_id", "customer_name", "customer_type", "city"],
        how="left",
        validate="one_to_one",
    )
    summary[["revenue", "gross_profit", "orders"]] = summary[
        ["revenue", "gross_profit", "orders"]
    ].fillna(0)
    summary["orders"] = summary["orders"].astype(int)
    return summary.sort_values(["revenue", "customer_id"], ascending=[False, True]).reset_index(
        drop=True
    )


def build_dashboard_data(
    clean: dict[str, pd.DataFrame],
    quality_log: pd.DataFrame | None = None,
    raw_profile: pd.DataFrame | None = None,
) -> dict[str, pd.DataFrame]:
    """Prepare all data frames displayed by the Streamlit demo.

    Optional quality/profile frames come directly from the same pipeline run, so the
    dashboard never needs to invent placeholder quality metrics.
    """
    sales_lines = build_sales_lines(clean)
    inventory_view = build_inventory_view(clean, sales_lines)
    customers = build_customer_summary(sales_lines, clean["customers"])
    result = {"sales_lines": sales_lines, "inventory": inventory_view, "customers": customers}
    if quality_log is not None:
        result["quality_log"] = quality_log.copy()
    if raw_profile is not None:
        result["raw_profile"] = raw_profile.copy()
    return result


def sales_summary(sales_lines: pd.DataFrame) -> dict[str, float | int | None]:
    """Calculate headline metrics from the currently filtered line-level data."""
    revenue = float(sales_lines["net_revenue"].sum())
    profit = float(sales_lines["gross_profit"].sum())
    order_count = int(sales_lines["order_id"].nunique())
    customer_count = int(sales_lines["customer_id"].nunique())
    units = int(sales_lines["quantity"].sum())
    return {
        "revenue": revenue,
        "gross_profit": profit,
        "margin_pct": (100 * profit / revenue) if revenue else None,
        "orders": order_count,
        "customers": customer_count,
        "average_order_value": (revenue / order_count) if order_count else None,
        "units_sold": units,
    }


def monthly_sales(sales_lines: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the filtered sales lines to month, with month-over-month growth."""
    if sales_lines.empty:
        return pd.DataFrame(
            columns=["month", "revenue", "gross_profit", "orders", "margin_pct", "mom_growth_pct"]
        )
    rows = sales_lines.assign(month=sales_lines["order_date"].dt.to_period("M").dt.to_timestamp())
    monthly = rows.groupby("month", as_index=False).agg(
        revenue=("net_revenue", "sum"),
        gross_profit=("gross_profit", "sum"),
        orders=("order_id", "nunique"),
    )
    monthly["margin_pct"] = np.where(
        monthly["revenue"].ne(0), 100 * monthly["gross_profit"] / monthly["revenue"], np.nan
    )
    monthly["mom_growth_pct"] = monthly["revenue"].pct_change() * 100
    return monthly


def format_inr(value: float | int | None) -> str:
    """Format a value in Indian rupees, using compact units for dashboard cards."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    amount = float(value)
    absolute = abs(amount)
    if absolute >= 10_000_000:
        return f"₹{amount / 10_000_000:,.2f} Cr"
    if absolute >= 100_000:
        return f"₹{amount / 100_000:,.2f} L"
    return f"₹{amount:,.0f}"


def inventory_summary(inventory_view: pd.DataFrame) -> dict[str, float | int]:
    """Calculate summary statistics and capital requirements across inventory positions."""
    if inventory_view.empty:
        return {
            "total_positions": 0,
            "total_inventory_value": 0.0,
            "stockout_positions": 0,
            "below_reorder_positions": 0,
            "replenishment_units_required": 0,
            "replenishment_cost_estimate": 0.0,
            "stock_gap_retail_val": 0.0,
            "suggested_order_units": 0,
        }

    repl_units = (
        int(inventory_view["replenishment_qty_required"].sum())
        if "replenishment_qty_required" in inventory_view
        else int(
            np.maximum(
                0, inventory_view["reorder_level"] - inventory_view["quantity_on_hand"]
            ).sum()
        )
    )

    repl_cost = (
        round(float(inventory_view["replenishment_cost_estimate"].sum()), 2)
        if "replenishment_cost_estimate" in inventory_view
        else round(
            float(
                (
                    np.maximum(
                        0, inventory_view["reorder_level"] - inventory_view["quantity_on_hand"]
                    )
                    * inventory_view["cost_price"]
                ).sum()
            ),
            2,
        )
    )

    stock_gap_retail = (
        round(float(inventory_view["stock_gap_retail_val"].sum()), 2)
        if "stock_gap_retail_val" in inventory_view
        else round(
            float(
                (
                    np.maximum(
                        0, inventory_view["reorder_level"] - inventory_view["quantity_on_hand"]
                    )
                    * inventory_view["selling_price"]
                ).sum()
            ),
            2,
        )
    )

    return {
        "total_positions": int(len(inventory_view)),
        "total_inventory_value": round(float(inventory_view["inventory_value"].sum()), 2),
        "stockout_positions": int(inventory_view["quantity_on_hand"].eq(0).sum()),
        "below_reorder_positions": int(
            (inventory_view["quantity_on_hand"] < inventory_view["reorder_level"]).sum()
        ),
        "replenishment_units_required": repl_units,
        "replenishment_cost_estimate": repl_cost,
        "stock_gap_retail_val": stock_gap_retail,
        "suggested_order_units": int(
            inventory_view["suggested_order_qty"].sum()
            if "suggested_order_qty" in inventory_view
            else 0
        ),
    }


def simulate_price_sensitivity(
    sales_lines: pd.DataFrame,
    product_id: str,
    price_change_pct: float,
    volume_change_pct: float | None = None,
    elasticity: float | None = None,
) -> dict[str, Any]:
    """Model the financial impact of price changes on revenue and gross profit.

    Parameters
    ----------
    sales_lines : pd.DataFrame
        Cleaned sales lines containing completed orders.
    product_id : str
        Target product identifier (e.g. 'P0010').
    price_change_pct : float
        Percentage price increase/decrease (+3.0 for +3%).
    volume_change_pct : float | None
        Assumed percentage change in unit volume (-4.5 for -4.5%).
    elasticity : float | None
        Price elasticity of demand magnitude (e.g. 1.5 or -1.5).
        If provided and volume_change_pct is None, volume change is modeled as
        volume_change_pct = -abs(elasticity) * price_change_pct.

    Returns
    -------
    dict[str, Any]
        Dictionary with baseline and modeled metrics, deltas, and break-even volume decline.
    """
    prod_lines = sales_lines.loc[sales_lines["product_id"] == product_id]
    if prod_lines.empty:
        raise ValueError(f"Product '{product_id}' not found in sales lines.")

    product_name = str(prod_lines["product_name"].iloc[0])
    category_name = str(prod_lines["category_name"].iloc[0])

    baseline_units = int(prod_lines["quantity"].sum())
    baseline_revenue = round(float(prod_lines["net_revenue"].sum()), 2)
    baseline_cogs = round(float((prod_lines["quantity"] * prod_lines["cost_price"]).sum()), 2)
    baseline_profit = round(baseline_revenue - baseline_cogs, 2)
    baseline_margin_pct = (
        round(100.0 * baseline_profit / baseline_revenue, 2) if baseline_revenue > 0 else 0.0
    )

    p_pct = float(price_change_pct)
    if volume_change_pct is not None:
        v_pct = float(volume_change_pct)
        assumed_elasticity = round(v_pct / p_pct, 2) if p_pct != 0 else 0.0
    elif elasticity is not None:
        e = -abs(float(elasticity))
        v_pct = round(e * p_pct, 2)
        assumed_elasticity = round(e, 2)
    else:
        v_pct = 0.0
        assumed_elasticity = 0.0

    p_factor = 1.0 + (p_pct / 100.0)
    v_factor = 1.0 + (v_pct / 100.0)

    modeled_units = max(0, int(round(baseline_units * v_factor)))
    modeled_revenue = round(baseline_revenue * p_factor * v_factor, 2)
    modeled_cogs = round(baseline_cogs * v_factor, 2)
    modeled_profit = round(modeled_revenue - modeled_cogs, 2)
    modeled_margin_pct = (
        round(100.0 * modeled_profit / modeled_revenue, 2) if modeled_revenue > 0 else 0.0
    )

    delta_revenue = round(modeled_revenue - baseline_revenue, 2)
    delta_profit = round(modeled_profit - baseline_profit, 2)
    delta_margin_points = round(modeled_margin_pct - baseline_margin_pct, 2)

    # Break-even volume decline:
    # Modeled profit = [R0*(1+p) - C0] * (1 - decline) = G0
    # decline = 1 - G0 / [R0*(1+p) - C0]
    denom = (baseline_revenue * p_factor) - baseline_cogs
    if denom > 0:
        be_decline_pct = round((1.0 - (baseline_profit / denom)) * 100.0, 2)
    else:
        be_decline_pct = None

    return {
        "product_id": product_id,
        "product_name": product_name,
        "category_name": category_name,
        "price_change_pct": p_pct,
        "volume_change_pct": v_pct,
        "assumed_elasticity": assumed_elasticity,
        "baseline": {
            "units": baseline_units,
            "revenue": baseline_revenue,
            "cogs": baseline_cogs,
            "gross_profit": baseline_profit,
            "margin_pct": baseline_margin_pct,
        },
        "modeled": {
            "units": modeled_units,
            "revenue": modeled_revenue,
            "cogs": modeled_cogs,
            "gross_profit": modeled_profit,
            "margin_pct": modeled_margin_pct,
        },
        "delta": {
            "revenue": delta_revenue,
            "gross_profit": delta_profit,
            "margin_points": delta_margin_points,
        },
        "break_even_volume_decline_pct": be_decline_pct,
    }
