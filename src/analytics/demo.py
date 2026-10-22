"""Pandas calculations used by the no-database InsightFlow demo dashboard.

The dashboard uses the same cleaned synthetic inputs as the PostgreSQL pipeline. The
SQL views remain the canonical implementation for the full database/API stack; these
pandas functions make the interactive demo usable without PostgreSQL credentials.
"""

from __future__ import annotations

import math

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
