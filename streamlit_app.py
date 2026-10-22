"""Interactive InsightFlow demo dashboard; requires no PostgreSQL credentials."""

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics.demo import build_dashboard_data, format_inr, monthly_sales, sales_summary
from src.config import PROJECT_ROOT
from src.pipeline import clean_raw_files

DATA_AS_OF = date(2026, 9, 30)

st.set_page_config(
    page_title="InsightFlow | Sales & Inventory Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .stApp { background: #f4f7fb; }
      [data-testid="stHeader"] { background: rgba(244,247,251,.92); }
      [data-testid="stSidebar"] { background: #14243a; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
      [data-testid="stSidebar"] label,
      [data-testid="stSidebar"] p,
      [data-testid="stSidebar"] h1,
      [data-testid="stSidebar"] h2,
      [data-testid="stSidebar"] h3 { color: #edf4ff !important; }
      [data-testid="stMetric"] {
        background: #ffffff; border: 1px solid #dce5f0; border-radius: 13px;
        padding: 16px 18px; box-shadow: 0 2px 8px rgba(16,35,60,.035);
      }
      [data-testid="stMetricLabel"] { color: #62748b; }
      [data-testid="stMetricValue"] { color: #15253b; }
      div[data-testid="stPlotlyChart"] {
        background: #ffffff; border: 1px solid #dce5f0; border-radius: 13px;
        padding: 6px 8px; overflow: hidden;
      }
      .if-eyebrow {
        color: #2764df; font-size: .74rem; font-weight: 750;
        letter-spacing: .12em; text-transform: uppercase; margin-bottom: .25rem;
      }
      .if-note {
        border: 1px solid #cfe0fb; background: #edf4ff; color: #31547e;
        border-radius: 10px; padding: 11px 14px; font-size: .88rem;
      }
      .if-section-note { color: #65758b; font-size: .88rem; margin-top: -.35rem; }
      div[data-testid="stDataFrame"] {
        border: 1px solid #dce5f0;
        border-radius: 12px;
        overflow: hidden;
      }
      .block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1540px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Profiling and cleaning the synthetic source files...")
def load_demo_data() -> dict[str, pd.DataFrame]:
    """Use the same ingestion, cleaning and validation pipeline as the backend."""
    result = clean_raw_files(PROJECT_ROOT / "data" / "raw", DATA_AS_OF)
    return build_dashboard_data(result.clean, result.quality_log, result.profile)


try:
    data = load_demo_data()
except Exception as exc:  # display a helpful message instead of a blank app on bad setup
    st.error("InsightFlow could not prepare the demo dataset.")
    st.exception(exc)
    st.stop()

sales = data["sales_lines"]
inventory = data["inventory"]
customers = data["customers"]
quality_log = data["quality_log"]
raw_profile = data["raw_profile"]

st.sidebar.markdown("# InsightFlow")
st.sidebar.caption("SALES & INVENTORY INTELLIGENCE")
st.sidebar.markdown(
    "<div style='border:1px solid #3b5270;border-radius:9px;padding:9px 11px;"
    "color:#c6dcfa;font-size:12px;'>"
    "DEMO MODE · SYNTHETIC DATA</div>",
    unsafe_allow_html=True,
)
st.sidebar.markdown(" ")
page = st.sidebar.radio(
    "WORKSPACE",
    [
        "Executive Overview",
        "Sales & Products",
        "Inventory Intelligence",
        "Customers & Data Quality",
    ],
)

min_day = sales["order_date"].min().date()
max_day = sales["order_date"].max().date()
st.sidebar.markdown("---")
st.sidebar.markdown("### Filters")
selected_dates = st.sidebar.date_input(
    "Order date range",
    value=(min_day, max_day),
    min_value=min_day,
    max_value=max_day,
    help="Applies to sales and customer activity. Inventory is a snapshot dated 30 September 2026.",
)
if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
elif isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 1:
    start_date = end_date = selected_dates[0]
else:
    start_date = end_date = selected_dates

region_options = sorted(sales["region"].dropna().unique().tolist())
category_options = sorted(sales["category_name"].dropna().unique().tolist())
customer_type_options = sorted(sales["customer_type"].dropna().unique().tolist())
selected_regions = st.sidebar.multiselect("Region", region_options, default=region_options)
selected_categories = st.sidebar.multiselect("Category", category_options, default=category_options)
selected_customer_types = st.sidebar.multiselect(
    "Customer type", customer_type_options, default=customer_type_options
)
st.sidebar.markdown("---")
st.sidebar.caption("Snapshot date: 30 Sep 2026")
st.sidebar.caption("No database connection or external API key is needed for this demo dashboard.")

filtered_sales = sales.loc[
    sales["order_date"].dt.date.between(start_date, end_date)
    & sales["region"].isin(selected_regions)
    & sales["category_name"].isin(selected_categories)
    & sales["customer_type"].isin(selected_customer_types)
].copy()
filtered_inventory = inventory.loc[
    inventory["region"].isin(selected_regions)
    & inventory["category_name"].isin(selected_categories)
].copy()
st.markdown(
    '<div class="if-eyebrow">Business intelligence · portfolio demo</div>',
    unsafe_allow_html=True,
)
st.title("InsightFlow")
st.markdown(
    "Turn inconsistent sales and inventory exports into cleaner data, decision-ready metrics, "
    "and reviewable exceptions."
)
st.markdown(
    '<div class="if-note"><strong>Demo data notice:</strong> All records and business figures '
    "are synthetic. The interactive dashboard runs the project's real ingestion, cleaning and "
    "validation pipeline; the PostgreSQL / SQL / API stack is documented separately.</div>",
    unsafe_allow_html=True,
)
st.write("")


def metric_row(frame: pd.DataFrame) -> None:
    summary = sales_summary(frame)
    cols = st.columns(5)
    cols[0].metric("Net revenue", format_inr(summary["revenue"]))
    cols[1].metric("Gross profit", format_inr(summary["gross_profit"]))
    cols[2].metric(
        "Gross margin",
        f"{summary['margin_pct']:.1f}%" if summary["margin_pct"] is not None else "—",
    )
    cols[3].metric("Completed orders", f"{summary['orders']:,}")
    cols[4].metric("Average order value", format_inr(summary["average_order_value"]))


def style_chart(fig, height: int = 340):
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=18, r=18, t=56, b=18),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(family="Inter, Segoe UI, Arial, sans-serif", color="#24364b", size=12),
        title=dict(font=dict(size=15, color="#15253b"), x=0.02, xanchor="left"),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0.02),
    )
    fig.update_xaxes(showgrid=False, linecolor="#e5ebf3", zeroline=False)
    fig.update_yaxes(gridcolor="#edf1f6", zeroline=False)
    return fig


if page == "Executive Overview":
    metric_row(filtered_sales)
    monthly = monthly_sales(filtered_sales)
    left, right = st.columns([1.55, 1])
    with left:
        if not monthly.empty:
            fig = px.line(
                monthly,
                x="month",
                y="revenue",
                markers=True,
                title="Monthly net revenue",
                labels={"month": "Month", "revenue": "Net revenue (₹)"},
            )
            fig.update_traces(line_color="#2764df", line_width=3, marker_size=6)
            st.plotly_chart(style_chart(fig), use_container_width=True)
        else:
            st.info("No sales match the selected filters.")
    with right:
        by_region = (
            filtered_sales.groupby("region", as_index=False)["net_revenue"]
            .sum()
            .sort_values("net_revenue", ascending=True)
        )
        fig = px.bar(
            by_region,
            x="net_revenue",
            y="region",
            orientation="h",
            title="Revenue by region",
            labels={"region": "Region", "net_revenue": "Net revenue (₹)"},
            color_discrete_sequence=["#4b8bf4"],
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)

    left, right = st.columns([1, 1.25])
    with left:
        category = (
            filtered_sales.groupby("category_name", as_index=False)["net_revenue"]
            .sum()
            .sort_values("net_revenue", ascending=True)
        )
        fig = px.bar(
            category,
            x="net_revenue",
            y="category_name",
            orientation="h",
            title="Category contribution",
            labels={"category_name": "Category", "net_revenue": "Net revenue (₹)"},
            color_discrete_sequence=["#178b73"],
        )
        st.plotly_chart(style_chart(fig, 360), use_container_width=True)
    with right:
        st.subheader("Inventory signals")
        action_statuses = ["Out of stock", "Stock-out risk", "Low stock"]
        needs_action = filtered_inventory.loc[
            filtered_inventory["stock_status"].isin(action_statuses)
        ]
        cols = st.columns(3)
        cols[0].metric("Stock positions", f"{len(filtered_inventory):,}")
        cols[1].metric("Need review", f"{len(needs_action):,}")
        cols[2].metric("Suggested units", f"{needs_action['suggested_order_qty'].sum():,}")
        by_status = (
            filtered_inventory.groupby("stock_status", as_index=False)
            .size()
            .rename(columns={"size": "positions"})
            .sort_values("positions", ascending=False)
        )
        fig = px.bar(
            by_status,
            x="stock_status",
            y="positions",
            title="Stock status distribution",
            labels={"stock_status": "Status", "positions": "Stock positions"},
            color="stock_status",
            color_discrete_map={
                "Out of stock": "#d64b55",
                "Stock-out risk": "#e59a34",
                "Low stock": "#d8b34d",
                "Overstocked": "#8d7ee8",
                "Healthy": "#1f9a7a",
                "No recent sales": "#8998aa",
            },
        )
        st.plotly_chart(style_chart(fig, 300), use_container_width=True)

    st.subheader("Products with highest net revenue")
    top = (
        filtered_sales.groupby(["product_name", "category_name"], as_index=False)
        .agg(
            net_revenue=("net_revenue", "sum"),
            gross_profit=("gross_profit", "sum"),
            units=("quantity", "sum"),
        )
        .sort_values("net_revenue", ascending=False)
        .head(8)
    )
    if not top.empty:
        top["Net revenue"] = top["net_revenue"].map(format_inr)
        top["Gross profit"] = top["gross_profit"].map(format_inr)
        top = top.rename(
            columns={"product_name": "Product", "category_name": "Category", "units": "Units sold"}
        )
        st.dataframe(
            top[["Product", "Category", "Units sold", "Net revenue", "Gross profit"]],
            use_container_width=True,
            hide_index=True,
        )

elif page == "Sales & Products":
    st.subheader("Sales & Product Performance")
    st.markdown(
        '<p class="if-section-note">Explore revenue trends, margin contribution and product '
        "performance using the selected filters.</p>",
        unsafe_allow_html=True,
    )
    metric_row(filtered_sales)
    monthly = monthly_sales(filtered_sales)
    if not monthly.empty:
        left, right = st.columns(2)
        with left:
            fig = px.bar(
                monthly,
                x="month",
                y="revenue",
                title="Monthly revenue",
                labels={"month": "Month", "revenue": "Net revenue (₹)"},
                color_discrete_sequence=["#2764df"],
            )
            st.plotly_chart(style_chart(fig), use_container_width=True)
        with right:
            fig = px.line(
                monthly,
                x="month",
                y="margin_pct",
                title="Gross margin trend",
                labels={"month": "Month", "margin_pct": "Margin (%)"},
                markers=True,
                color_discrete_sequence=["#138a63"],
            )
            st.plotly_chart(style_chart(fig), use_container_width=True)
    product = filtered_sales.groupby(["product_name", "category_name"], as_index=False).agg(
        net_revenue=("net_revenue", "sum"),
        gross_profit=("gross_profit", "sum"),
        units=("quantity", "sum"),
    )
    if not product.empty:
        product["margin_pct"] = (
            100 * product["gross_profit"] / product["net_revenue"].replace(0, pd.NA)
        ).round(1)
        fig = px.scatter(
            product,
            x="net_revenue",
            y="gross_profit",
            size="units",
            color="category_name",
            hover_name="product_name",
            title="Product revenue vs. gross profit",
            labels={
                "net_revenue": "Net revenue (₹)",
                "gross_profit": "Gross profit (₹)",
                "category_name": "Category",
            },
        )
        st.plotly_chart(style_chart(fig, 420), use_container_width=True)
        display = product.sort_values("net_revenue", ascending=False).rename(
            columns={
                "product_name": "Product",
                "category_name": "Category",
                "net_revenue": "Net revenue (₹)",
                "gross_profit": "Gross profit (₹)",
                "units": "Units sold",
                "margin_pct": "Margin (%)",
            }
        )
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.download_button(
            "Download filtered sales lines (CSV)",
            filtered_sales.to_csv(index=False).encode("utf-8"),
            file_name="insightflow_sales_lines.csv",
            mime="text/csv",
        )
    else:
        st.info("No sales match the selected filters.")

elif page == "Inventory Intelligence":
    st.subheader("Inventory Intelligence")
    st.markdown(
        '<p class="if-section-note">The current inventory snapshot is 30 September 2026. '
        "Suggested order quantities are simple threshold-based planning aids, not demand forecasts."
        "</p>",
        unsafe_allow_html=True,
    )
    action_statuses = ["Out of stock", "Stock-out risk", "Low stock"]
    needs_action = filtered_inventory.loc[filtered_inventory["stock_status"].isin(action_statuses)]
    inv_value = float(filtered_inventory["inventory_value"].sum())
    cols = st.columns(4)
    cols[0].metric("Inventory value", format_inr(inv_value))
    cols[1].metric("Positions needing review", f"{len(needs_action):,}")
    cols[2].metric(
        "Out of stock",
        f"{int(filtered_inventory['stock_status'].eq('Out of stock').sum()):,}",
    )
    cols[3].metric("Suggested order units", f"{int(needs_action['suggested_order_qty'].sum()):,}")
    left, right = st.columns(2)
    with left:
        status_df = (
            filtered_inventory.groupby("stock_status", as_index=False)
            .size()
            .rename(columns={"size": "positions"})
        )
        fig = px.pie(
            status_df,
            names="stock_status",
            values="positions",
            hole=0.62,
            title="Stock position mix",
            color="stock_status",
            color_discrete_map={
                "Out of stock": "#d64b55",
                "Stock-out risk": "#e59a34",
                "Low stock": "#d8b34d",
                "Overstocked": "#8d7ee8",
                "Healthy": "#1f9a7a",
                "No recent sales": "#8998aa",
            },
        )
        fig.update_traces(textposition="inside", textinfo="percent")
        st.plotly_chart(style_chart(fig, 380), use_container_width=True)
    with right:
        by_category = (
            filtered_inventory.groupby("category_name", as_index=False)["inventory_value"]
            .sum()
            .sort_values("inventory_value", ascending=True)
        )
        fig = px.bar(
            by_category,
            x="inventory_value",
            y="category_name",
            orientation="h",
            title="Inventory value by category",
            labels={"category_name": "Category", "inventory_value": "Inventory value (₹)"},
            color_discrete_sequence=["#4b8bf4"],
        )
        st.plotly_chart(style_chart(fig, 380), use_container_width=True)
    st.subheader("Priority review queue")
    if not needs_action.empty:
        priority = {"Out of stock": 1, "Stock-out risk": 2, "Low stock": 3}
        needs_action = needs_action.assign(_priority=needs_action["stock_status"].map(priority))
        needs_action = needs_action.sort_values(
            ["_priority", "suggested_order_qty"], ascending=[True, False]
        )
        display = needs_action[
            [
                "product_name",
                "category_name",
                "location_name",
                "quantity_on_hand",
                "reorder_level",
                "avg_daily_units",
                "days_of_cover",
                "stock_status",
                "suggested_order_qty",
            ]
        ].rename(
            columns={
                "product_name": "Product",
                "category_name": "Category",
                "location_name": "Location",
                "quantity_on_hand": "On hand",
                "reorder_level": "Reorder level",
                "avg_daily_units": "Avg units/day",
                "days_of_cover": "Days of cover",
                "stock_status": "Status",
                "suggested_order_qty": "Suggested order",
            }
        )
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.download_button(
            "Download inventory review queue (CSV)",
            display.to_csv(index=False).encode("utf-8"),
            file_name="insightflow_inventory_review.csv",
            mime="text/csv",
        )
    else:
        st.success("No inventory positions require action under the selected filters.")

else:
    st.subheader("Customers & Data Quality")
    st.markdown(
        '<p class="if-section-note">Customer activity is calculated from completed orders. '
        "Quality events are logged actions; one row can contribute to more than one issue "
        "category.</p>",
        unsafe_allow_html=True,
    )
    total_customers = int(filtered_sales["customer_id"].nunique())
    repeat_customers = (
        int(filtered_sales.groupby("customer_id")["order_id"].nunique().ge(2).sum())
        if not filtered_sales.empty
        else 0
    )
    cols = st.columns(4)
    cols[0].metric("Buying customers", f"{total_customers:,}")
    cols[1].metric("Repeat customers", f"{repeat_customers:,}")
    cols[2].metric("Quality actions logged", f"{len(quality_log):,}")
    cols[3].metric("Source fields profiled", f"{len(raw_profile):,}")
    left, right = st.columns(2)
    customer_type = filtered_sales.groupby("customer_type", as_index=False).agg(
        revenue=("net_revenue", "sum"), customers=("customer_id", "nunique")
    )
    with left:
        fig = px.bar(
            customer_type,
            x="customer_type",
            y="revenue",
            title="Revenue by customer type",
            labels={"customer_type": "Customer type", "revenue": "Net revenue (₹)"},
            color_discrete_sequence=["#2764df"],
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)
    with right:
        top_customers = (
            filtered_sales.groupby(["customer_name", "customer_type", "city"], as_index=False)
            .agg(revenue=("net_revenue", "sum"), orders=("order_id", "nunique"))
            .sort_values("revenue", ascending=False)
            .head(10)
        )
        fig = px.bar(
            top_customers.sort_values("revenue"),
            x="revenue",
            y="customer_name",
            color="customer_type",
            orientation="h",
            title="Top customers by revenue",
            labels={
                "customer_name": "Customer",
                "revenue": "Net revenue (₹)",
                "customer_type": "Type",
            },
        )
        st.plotly_chart(style_chart(fig), use_container_width=True)
    st.subheader("Data quality actions")
    quality_display = quality_log.sort_values("rows_affected", ascending=False).rename(
        columns={
            "table_name": "Source table",
            "issue": "Issue detected",
            "rows_affected": "Rows affected",
            "action": "Action taken",
        }
    )
    st.dataframe(quality_display, use_container_width=True, hide_index=True)
    st.subheader("Raw source profile")
    missing = raw_profile.loc[raw_profile["missing"].gt(0)].sort_values(
        ["missing", "missing_pct"], ascending=False
    )
    missing_display = missing.rename(
        columns={
            "table_name": "Source table",
            "column_name": "Column",
            "rows": "Source rows",
            "missing": "Missing cells",
            "missing_pct": "Missing (%)",
            "distinct": "Distinct values",
            "plain_number_pct": "Plain-number (%)",
        }
    )
    st.dataframe(missing_display, use_container_width=True, hide_index=True)

st.caption(
    "Method note: synthetic data only. Revenue excludes cancelled and returned orders. "
    "Profit uses the current product cost because the source dataset has no historical cost. "
    "Inventory is a snapshot; the suggested order quantity is not a demand forecast."
)
st.markdown(
    "[Source code](https://github.com/meetpokal1/InsightFlow) · "
    "[Project documentation](README.md) · "
    "[API and PostgreSQL architecture](documentation/api.md)"
)
