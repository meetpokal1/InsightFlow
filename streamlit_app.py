"""Interactive InsightFlow demo dashboard; requires no PostgreSQL credentials."""

import math
from datetime import date
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics.demo import (
    build_dashboard_data,
    format_inr,
    inventory_summary,
    monthly_sales,
    sales_summary,
    simulate_price_sensitivity,
)
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
      .stApp { background: #f8fafc; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
      [data-testid="stHeader"] { background: rgba(248,250,252,.92); backdrop-filter: blur(8px); }
      [data-testid="stSidebar"] { background: #0f172a; }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {
        color: #f8fafc !important; font-size: 1.45rem; font-weight: 750;
        letter-spacing: -0.01em; margin-bottom: 0.1rem;
      }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
        color: #e2e8f0 !important; font-size: 1rem; font-weight: 700;
        margin-top: 0.75rem; margin-bottom: 0.35rem;
      }
      [data-testid="stSidebar"] .stCaption,
      [data-testid="stSidebar"] p { color: #94a3b8 !important; }
      [data-testid="stSidebar"] label {
        color: #e2e8f0 !important; font-weight: 600 !important; font-size: 0.86rem !important;
      }
      .if-sidebar-badge {
        display: inline-block; border: 1px solid #334155; border-radius: 6px;
        padding: 5px 9px; color: #93c5fd; font-size: 0.72rem; font-weight: 650;
        letter-spacing: 0.05em; background: rgba(30, 41, 59, 0.6); margin-top: 0.25rem;
      }
      h1 {
        color: #0f172a !important; font-weight: 750 !important;
        letter-spacing: -0.02em !important; margin-top: 0 !important;
        padding-top: 0 !important; margin-bottom: 0.3rem !important;
      }
      h2, h3 {
        color: #1e293b !important; font-weight: 700 !important;
        letter-spacing: -0.01em !important;
      }
      [data-testid="stMetric"] {
        background: #ffffff; border: 1px solid #e2e8f0; border-top: 3px solid #2563eb;
        border-radius: 10px; padding: 12px 14px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        min-width: 0;
      }
      [data-testid="stMetricLabel"] {
        color: #64748b !important; font-size: 0.78rem !important; font-weight: 650 !important;
        text-transform: uppercase; letter-spacing: 0.03em;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
      }
      [data-testid="stMetricValue"] {
        color: #0f172a !important; font-weight: 750 !important; letter-spacing: -0.02em !important;
        font-size: clamp(1.2rem, 1.45vw, 1.6rem) !important;
        line-height: 1.25 !important;
        white-space: nowrap !important;
        overflow: visible !important;
      }
      [data-testid="stMetricValue"] > div {
        font-size: inherit !important;
        line-height: inherit !important;
        white-space: nowrap !important;
        overflow: visible !important;
      }
      div[data-testid="stPlotlyChart"] {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px;
        padding: 8px 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); overflow: hidden;
      }
      .if-eyebrow {
        display: inline-flex; align-items: center; background: #eff6ff;
        color: #1e40af; border: 1px solid #bfdbfe; border-radius: 9999px;
        padding: 4px 12px; font-size: 0.76rem; font-weight: 700;
        letter-spacing: 0.05em; text-transform: uppercase; line-height: 1.4;
        margin-bottom: 0.4rem;
      }
      .if-subtitle {
        color: #475569; font-size: 1.02rem; line-height: 1.45;
        margin-top: -0.1rem; margin-bottom: 0.75rem;
      }
      .if-briefing {
        background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid #2563eb;
        border-radius: 10px; padding: 12px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-top: 0.25rem; margin-bottom: 1.25rem;
      }
      .if-briefing-header {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 6px; flex-wrap: wrap; gap: 8px;
      }
      .if-briefing-tag {
        font-size: 0.72rem; font-weight: 750; letter-spacing: 0.05em;
        text-transform: uppercase; color: #1e40af; background: #eff6ff;
        border: 1px solid #dbeafe; padding: 2px 8px; border-radius: 9999px;
      }
      .if-briefing-date {
        font-size: 0.78rem; color: #64748b; font-weight: 500;
      }
      .if-briefing-text {
        color: #334155; font-size: 0.88rem; line-height: 1.5; margin: 0;
      }
      .if-briefing-text strong { color: #0f172a; }
      .if-note {
        border: 1px solid #dbeafe; background: #eff6ff; color: #1e40af;
        border-radius: 10px; padding: 12px 16px; font-size: 0.88rem;
        line-height: 1.45; margin-bottom: 1.25rem;
      }
      .if-note strong { color: #1e3a8a; }
      .if-section-note {
        color: #64748b; font-size: 0.88rem; line-height: 1.4;
        margin-top: -0.25rem; margin-bottom: 1rem;
      }
      div[data-testid="stDataFrame"] {
        background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04); overflow: hidden;
      }
      .block-container {
        padding-top: 4.5rem !important; padding-bottom: 3.5rem !important; max-width: 1540px;
      }
      @media (max-width: 768px) {
        .block-container {
          padding-top: 3.75rem !important; padding-bottom: 2rem !important;
          padding-left: 1rem !important; padding-right: 1rem !important;
        }
        [data-testid="stMetric"] { padding: 12px 14px; }
        .if-eyebrow { font-size: 0.72rem; padding: 4px 11px; }
        .if-subtitle { font-size: 0.94rem; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Profiling and cleaning the synthetic source files...")
def load_demo_data() -> dict[str, Any]:
    """Use the same ingestion, cleaning and validation pipeline as the backend."""
    result = clean_raw_files(PROJECT_ROOT / "data" / "raw", DATA_AS_OF)
    return build_dashboard_data(
        clean=result.clean,
        quality_log=result.quality_log,
        raw_profile=result.profile,
        raw=result.raw,
    )


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
defect_impact = data.get("defect_impact")

st.sidebar.markdown("# InsightFlow")
st.sidebar.caption("SALES & INVENTORY INTELLIGENCE")
st.sidebar.markdown(
    '<div class="if-sidebar-badge">DEMO MODE · SYNTHETIC DATA</div>',
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
selected_regions = st.sidebar.multiselect(
    "Region",
    region_options,
    default=[],
    placeholder="All regions",
    help="Leave empty for all regions.",
)
selected_categories = st.sidebar.multiselect(
    "Category",
    category_options,
    default=[],
    placeholder="All categories",
    help="Leave empty for all categories.",
)
selected_customer_types = st.sidebar.multiselect(
    "Customer type",
    customer_type_options,
    default=[],
    placeholder="All customer types",
    help="Leave empty for all customer types.",
)
st.sidebar.markdown("---")
st.sidebar.caption("Snapshot date: 30 Sep 2026")
st.sidebar.caption("No database connection or external API key is needed for this demo dashboard.")

active_regions = selected_regions if selected_regions else region_options
active_categories = selected_categories if selected_categories else category_options
active_customer_types = (
    selected_customer_types if selected_customer_types else customer_type_options
)

filtered_sales = sales.loc[
    sales["order_date"].dt.date.between(start_date, end_date)
    & sales["region"].isin(active_regions)
    & sales["category_name"].isin(active_categories)
    & sales["customer_type"].isin(active_customer_types)
].copy()
filtered_inventory = inventory.loc[
    inventory["region"].isin(active_regions) & inventory["category_name"].isin(active_categories)
].copy()
st.markdown(
    '<div class="if-eyebrow">Business intelligence · portfolio demo</div>',
    unsafe_allow_html=True,
)
st.title("InsightFlow")
st.markdown(
    '<p class="if-subtitle">Turn inconsistent sales and inventory exports into cleaner data, '
    "decision-ready metrics, and reviewable exceptions.</p>",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="if-note"><strong>Demo data notice:</strong> All records and business figures '
    "are synthetic. The interactive dashboard runs the project's real ingestion, cleaning and "
    "validation pipeline; the PostgreSQL / SQL / API stack is documented separately.</div>",
    unsafe_allow_html=True,
)


def format_exact_inr(value: float | int | None) -> str:
    """Format an exact currency amount in INR for tooltips and inspectable details."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    return f"₹{float(value):,.2f}"


def metric_row(frame: pd.DataFrame) -> None:
    summary = sales_summary(frame)
    cols = st.columns(5)
    cols[0].metric(
        "Net revenue",
        format_inr(summary["revenue"]),
        help=f"Audited net turnover: {format_exact_inr(summary['revenue'])}",
    )
    cols[1].metric(
        "Gross profit",
        format_inr(summary["gross_profit"]),
        help=f"Audited gross profit: {format_exact_inr(summary['gross_profit'])}",
    )
    cols[2].metric(
        "Gross margin",
        f"{summary['margin_pct']:.1f}%" if summary["margin_pct"] is not None else "—",
        help="Gross Profit ÷ Net Revenue across fulfilled orders",
    )
    cols[3].metric(
        "Completed orders",
        f"{summary['orders']:,}",
        help=f"Total fulfilled customer orders: {summary['orders']:,}",
    )
    cols[4].metric(
        "Average order value",
        format_inr(summary["average_order_value"]),
        help=f"Audited average order value: {format_exact_inr(summary['average_order_value'])}",
    )


def style_chart(
    fig,
    height: int = 340,
    show_legend: bool = False,
    legend_position: str = "top-right",
):
    layout_update = dict(
        template="plotly_white",
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(
            family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
            color="#1e293b",
            size=12,
        ),
        title=dict(
            font=dict(
                size=14, color="#0f172a", family="Inter, -apple-system, Segoe UI, sans-serif"
            ),
            x=0.02,
            xanchor="left",
            y=0.96,
            yanchor="top",
        ),
        showlegend=show_legend,
        hoverlabel=dict(
            bgcolor="#0f172a",
            font_size=12,
            font_family="Inter, -apple-system, Segoe UI, sans-serif",
            font_color="#f8fafc",
            bordercolor="#334155",
        ),
    )

    if not show_legend:
        layout_update["margin"] = dict(l=18, r=18, t=46, b=18)
    elif legend_position == "top-right":
        layout_update["margin"] = dict(l=18, r=18, t=54, b=18)
        layout_update["legend"] = dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            x=0.98,
            xanchor="right",
            title=dict(text=""),
        )
    elif legend_position == "bottom":
        layout_update["margin"] = dict(l=18, r=18, t=46, b=58)
        layout_update["legend"] = dict(
            orientation="h",
            yanchor="top",
            y=-0.14,
            x=0.5,
            xanchor="center",
            title=dict(text=""),
        )
    elif legend_position == "right":
        layout_update["margin"] = dict(l=18, r=160, t=46, b=18)
        layout_update["legend"] = dict(
            orientation="v",
            yanchor="top",
            y=0.98,
            x=1.02,
            xanchor="left",
            title=dict(text=""),
        )

    fig.update_layout(**layout_update)
    fig.update_xaxes(showgrid=False, linecolor="#e2e8f0", zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor="#f1f5f9", zeroline=False, automargin=True)
    return fig


if page == "Executive Overview":
    st.markdown(
        """
        <div class="if-briefing">
          <div class="if-briefing-header">
            <span class="if-briefing-tag">Executive Briefing · Flagship Turnover</span>
            <span class="if-briefing-date">Period: FY 2025–26 (Data as of 30 Sep 2026)</span>
          </div>
          <p class="if-briefing-text">
            Commercial operations delivered <strong>₹20.90 Cr</strong> in audited net turnover across <strong>7,878</strong> fulfilled orders,
            maintaining an overall <strong>20.3%</strong> gross margin (₹4.24 Cr gross profit). Regional turnover is anchored by
            <strong>West (₹6.44 Cr)</strong> and <strong>North (₹5.88 Cr)</strong>. Supply chain alert: <strong>92 inventory positions</strong>
            require immediate replenishment review to prevent stockouts and restore buffer levels across active warehouses.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
            fig.update_traces(
                line_color="#1d4ed8",
                line_width=3,
                marker=dict(size=6, color="#1e40af"),
                hovertemplate="<b>%{x|%B %Y}</b><br>Net Revenue: ₹%{y:,.0f}<extra></extra>",
            )
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
            color_discrete_sequence=["#2563eb"],
        )
        fig.update_traces(
            hovertemplate="<b>%{y} Region</b><br>Net Revenue: ₹%{x:,.0f}<extra></extra>"
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
            color_discrete_sequence=["#0d9488"],
        )
        fig.update_traces(hovertemplate="<b>%{y}</b><br>Net Revenue: ₹%{x:,.0f}<extra></extra>")
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
                "Out of stock": "#dc2626",
                "Stock-out risk": "#ea580c",
                "Low stock": "#d97706",
                "Overstocked": "#7c3aed",
                "Healthy": "#059669",
                "No recent sales": "#94a3b8",
            },
        )
        fig.update_traces(hovertemplate="<b>%{x}</b><br>Positions: %{y:,}<extra></extra>")
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
        top["margin_pct"] = (100 * top["gross_profit"] / top["net_revenue"]).round(1)
        top["Margin %"] = top["margin_pct"].map(lambda v: f"{v:.1f}%")
        top["Net revenue"] = top["net_revenue"].map(format_inr)
        top["Gross profit"] = top["gross_profit"].map(format_inr)
        top["Units sold"] = top["units"].map(lambda v: f"{v:,}")
        top = top.rename(columns={"product_name": "Product", "category_name": "Category"})
        st.dataframe(
            top[["Product", "Category", "Units sold", "Net revenue", "Gross profit", "Margin %"]],
            use_container_width=True,
            hide_index=True,
        )

elif page == "Sales & Products":
    st.markdown(
        """
        <div class="if-briefing">
          <div class="if-briefing-header">
            <span class="if-briefing-tag">Commercial Intelligence · Margin & Price Optimization</span>
            <span class="if-briefing-date">Dynamic Demand Elasticity Engine</span>
          </div>
          <p class="if-briefing-text">
            Product margin analysis reveals structural divergence: staple high-volume lines like <strong>Basmati Rice 5kg (P0010)</strong>
            drive ₹1.64 Cr in gross sales but yield a slim <strong>2.15%</strong> margin, whereas specialty categories generate
            over <strong>30%</strong>. Use the scenario simulator below to model pricing changes, test price elasticity assumptions,
            and evaluate break-even volume drop buffers before initiating price adjustments.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
                color_discrete_sequence=["#2563eb"],
            )
            fig.update_traces(
                hovertemplate="<b>%{x|%B %Y}</b><br>Revenue: ₹%{y:,.0f}<extra></extra>"
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
                color_discrete_sequence=["#059669"],
            )
            fig.add_hline(
                y=20.26,
                line_dash="dash",
                line_color="#94a3b8",
                annotation_text="Target Benchmark (20.3%)",
                annotation_position="top left",
                annotation_font_size=11,
            )
            fig.update_traces(
                line_width=3,
                marker=dict(size=6, color="#047857"),
                hovertemplate="<b>%{x|%B %Y}</b><br>Gross Margin: %{y:.1f}%<extra></extra>",
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
            custom_data=["category_name", "units", "margin_pct"],
            title="Product revenue vs. gross profit (Bubble size = units sold)",
            labels={
                "net_revenue": "Net revenue (₹)",
                "gross_profit": "Gross profit (₹)",
                "category_name": "Category",
            },
        )
        fig.update_traces(
            hovertemplate="<b>%{hovertext}</b><br>Category: %{customdata[0]}<br>Net Revenue: ₹%{x:,.0f}<br>Gross Profit: ₹%{y:,.0f}<br>Units Sold: %{customdata[1]:,}<br>Margin: %{customdata[2]:.1f}%<extra></extra>"
        )
        st.plotly_chart(
            style_chart(fig, 440, show_legend=True, legend_position="right"),
            use_container_width=True,
        )
        display = product.sort_values("net_revenue", ascending=False).copy()
        display["Net revenue (₹)"] = display["net_revenue"].map(lambda x: f"₹{x:,.2f}")
        display["Gross profit (₹)"] = display["gross_profit"].map(lambda x: f"₹{x:,.2f}")
        display["Units sold"] = display["units"].map(lambda x: f"{x:,}")
        display["Margin (%)"] = display["margin_pct"].map(lambda x: f"{x:.1f}%")
        display = display.rename(
            columns={
                "product_name": "Product",
                "category_name": "Category",
            }
        )
        st.dataframe(
            display[
                [
                    "Product",
                    "Category",
                    "Units sold",
                    "Net revenue (₹)",
                    "Gross profit (₹)",
                    "Margin (%)",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.divider()
        with st.container(key="price-sensitivity-simulator"):
            st.subheader("Price & Margin Sensitivity Simulator")
            st.markdown(
                '<p class="if-section-note">Model the bottom-line financial impact of hypothetical price '
                "adjustments and customer demand responses. Initial defaults feature <strong>Basmati Rice 5kg (P0010)</strong>, "
                "InsightFlow's #1 revenue driver with a slim 2.15% margin.</p>",
                unsafe_allow_html=True,
            )

            sim_col1, sim_col2 = st.columns([1, 1])
            available_prods = (
                filtered_sales[["product_id", "product_name", "category_name"]]
                .drop_duplicates()
                .sort_values("product_name")
            )
            prod_options = {
                f"{row.product_name} ({row.product_id})": row.product_id
                for _, row in available_prods.iterrows()
            }

            default_idx = 0
            p0010_label = next((k for k, v in prod_options.items() if v == "P0010"), None)
            if p0010_label and p0010_label in prod_options:
                default_idx = list(prod_options.keys()).index(p0010_label)

            with sim_col1:
                selected_label = st.selectbox(
                    "Select product to simulate",
                    options=list(prod_options.keys()),
                    index=default_idx,
                    key="sim_product_select",
                )
                selected_prod_id = prod_options[selected_label]
                price_change = st.slider(
                    "Price adjustment (%)",
                    min_value=-15.0,
                    max_value=25.0,
                    value=3.0,
                    step=0.5,
                    key="sim_price_slider",
                )

            with sim_col2:
                demand_mode = st.radio(
                    "Demand response model",
                    options=[
                        "Assumed price elasticity of demand (|ε|)",
                        "Explicit volume change (%)",
                    ],
                    horizontal=True,
                    key="sim_demand_mode",
                )
                if demand_mode.startswith("Assumed price elasticity"):
                    elasticity_val = st.slider(
                        "Price elasticity of demand (|ε|)",
                        min_value=0.0,
                        max_value=3.0,
                        value=1.5,
                        step=0.1,
                        help="Assumed percentage demand drop per 1% price increase (e.g. 1.5 implies -4.5% volume at +3% price).",
                        key="sim_elasticity_slider",
                    )
                    sim_res = simulate_price_sensitivity(
                        sales_lines=filtered_sales,
                        product_id=selected_prod_id,
                        price_change_pct=price_change,
                        elasticity=elasticity_val,
                    )
                else:
                    vol_change = st.slider(
                        "Volume change (%)",
                        min_value=-50.0,
                        max_value=50.0,
                        value=-4.5,
                        step=0.5,
                        key="sim_vol_slider",
                    )
                    sim_res = simulate_price_sensitivity(
                        sales_lines=filtered_sales,
                        product_id=selected_prod_id,
                        price_change_pct=price_change,
                        volume_change_pct=vol_change,
                    )

            scols = st.columns(4)
            scols[0].metric(
                "Modeled Net Revenue",
                format_inr(sim_res["modeled"]["revenue"]),
                delta=f"{sim_res['delta']['revenue']:+,.0f} ₹",
            )
            scols[1].metric(
                "Modeled Gross Profit",
                format_inr(sim_res["modeled"]["gross_profit"]),
                delta=f"{sim_res['delta']['gross_profit']:+,.0f} ₹",
            )
            scols[2].metric(
                "Modeled Gross Margin",
                f"{sim_res['modeled']['margin_pct']:.2f}%",
                delta=f"{sim_res['delta']['margin_points']:+.2f} pts",
            )
            scols[3].metric(
                "Modeled Sales Units",
                f"{sim_res['modeled']['units']:,}",
                delta=f"{sim_res['modeled']['units'] - sim_res['baseline']['units']:+,} units",
            )

            # Visual Scenario Comparison Chart
            sim_chart_df = pd.DataFrame(
                [
                    {
                        "Metric": "Net Revenue",
                        "Scenario": "Baseline",
                        "Amount": sim_res["baseline"]["revenue"],
                    },
                    {
                        "Metric": "Net Revenue",
                        "Scenario": "Modeled",
                        "Amount": sim_res["modeled"]["revenue"],
                    },
                    {
                        "Metric": "Cost of Goods (COGS)",
                        "Scenario": "Baseline",
                        "Amount": sim_res["baseline"]["cogs"],
                    },
                    {
                        "Metric": "Cost of Goods (COGS)",
                        "Scenario": "Modeled",
                        "Amount": sim_res["modeled"]["cogs"],
                    },
                    {
                        "Metric": "Gross Profit",
                        "Scenario": "Baseline",
                        "Amount": sim_res["baseline"]["gross_profit"],
                    },
                    {
                        "Metric": "Gross Profit",
                        "Scenario": "Modeled",
                        "Amount": sim_res["modeled"]["gross_profit"],
                    },
                ]
            )
            fig_sim = px.bar(
                sim_chart_df,
                x="Metric",
                y="Amount",
                color="Scenario",
                barmode="group",
                title=f"Scenario Financial Comparison: {selected_label}",
                labels={"Amount": "Amount (₹)", "Metric": ""},
                color_discrete_map={
                    "Baseline": "#94a3b8",
                    "Modeled": "#2563eb" if sim_res["delta"]["gross_profit"] >= 0 else "#dc2626",
                },
            )
            fig_sim.update_traces(
                hovertemplate="<b>%{x} (%{data.name})</b><br>Amount: ₹%{y:,.0f}<extra></extra>"
            )
            st.plotly_chart(
                style_chart(fig_sim, height=300, show_legend=True, legend_position="top-right"),
                use_container_width=True,
            )

            be_pct = sim_res["break_even_volume_decline_pct"]
            if be_pct is not None and be_pct > 0:
                st.markdown(
                    f"""
                    <div style="background: rgba(16, 185, 129, 0.08); border-left: 4px solid #059669; border-radius: 6px; padding: 12px 18px; margin: 12px 0 14px 0;">
                        <div style="display: flex; align-items: baseline; gap: 12px;">
                            <span style="font-size: 1.5rem; font-weight: 700; color: #047857; line-height: 1;">{be_pct:.1f}%</span>
                            <span style="font-size: 0.95rem; font-weight: 600; color: #065f46;">Break-Even Volume Drop Buffer</span>
                        </div>
                        <div style="font-size: 0.85rem; color: #374151; margin-top: 4px;">
                            At a <strong>{price_change:+.1f}%</strong> price adjustment, customer sales volume can contract by up to <strong>{be_pct:.1f}%</strong> before baseline gross profit (₹{sim_res["baseline"]["gross_profit"]:,.2f}) is compromised.
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.success(
                    f"**Break-Even Tolerance:** At a **{price_change:+.1f}%** price adjustment, unit sales volume can decline by up to **{be_pct:.1f}%** before gross profit falls below the current baseline (₹{sim_res['baseline']['gross_profit']:,.2f})."
                )
            elif be_pct is not None:
                st.warning(
                    f"**Margin Dilution:** At {price_change:+.1f}% price, volume would need to increase by {-be_pct:.1f}% to preserve current profit."
                )

            sim_summary_df = pd.DataFrame(
                [
                    {
                        "Metric": "Net Revenue",
                        "Baseline": f"₹{sim_res['baseline']['revenue']:,.2f}",
                        "Modeled Scenario": f"₹{sim_res['modeled']['revenue']:,.2f}",
                        "Change (Δ)": f"{sim_res['delta']['revenue']:+,.2f} ₹",
                    },
                    {
                        "Metric": "Cost of Goods Sold (COGS)",
                        "Baseline": f"₹{sim_res['baseline']['cogs']:,.2f}",
                        "Modeled Scenario": f"₹{sim_res['modeled']['cogs']:,.2f}",
                        "Change (Δ)": f"{sim_res['modeled']['cogs'] - sim_res['baseline']['cogs']:+,.2f} ₹",
                    },
                    {
                        "Metric": "Gross Profit",
                        "Baseline": f"₹{sim_res['baseline']['gross_profit']:,.2f}",
                        "Modeled Scenario": f"₹{sim_res['modeled']['gross_profit']:,.2f}",
                        "Change (Δ)": f"{sim_res['delta']['gross_profit']:+,.2f} ₹",
                    },
                    {
                        "Metric": "Gross Margin %",
                        "Baseline": f"{sim_res['baseline']['margin_pct']:.2f}%",
                        "Modeled Scenario": f"{sim_res['modeled']['margin_pct']:.2f}%",
                        "Change (Δ)": f"{sim_res['delta']['margin_points']:+.2f}% pts",
                    },
                    {
                        "Metric": "Volume (Units Sold)",
                        "Baseline": f"{sim_res['baseline']['units']:,}",
                        "Modeled Scenario": f"{sim_res['modeled']['units']:,}",
                        "Change (Δ)": f"{sim_res['modeled']['units'] - sim_res['baseline']['units']:+,} units ({sim_res['volume_change_pct']:+.1f}%)",
                    },
                ]
            )
            st.dataframe(sim_summary_df, use_container_width=True, hide_index=True)
            st.caption(
                "Note: Elasticity values and demand responses are user-specified scenario planning parameters, not causal econometric estimates."
            )

        st.download_button(
            "Download filtered sales lines (CSV)",
            filtered_sales.to_csv(index=False).encode("utf-8"),
            file_name="insightflow_sales_lines.csv",
            mime="text/csv",
        )
    else:
        st.info("No sales match the selected filters.")

elif page == "Inventory Intelligence":
    st.markdown(
        """
        <div class="if-briefing">
          <div class="if-briefing-header">
            <span class="if-briefing-tag">Supply Chain Assurance · Working Capital & Replenishment</span>
            <span class="if-briefing-date">Snapshot: 30 September 2026</span>
          </div>
          <p class="if-briefing-text">
            Warehouse logistics monitor <strong>₹2.25 Cr</strong> in total inventory value across <strong>449</strong> active SKU locations.
            Currently, <strong>40 positions</strong> have zero stock on hand (true stockouts) and <strong>56 positions</strong> have fallen below
            safety reorder thresholds. Restoring buffer stock requires <strong>₹9.66 L</strong> in immediate working capital (5,791 units),
            protecting against <strong>₹13.41 L</strong> in downstream retail demand exposure.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("Inventory Intelligence")
    st.markdown(
        '<p class="if-section-note">The current inventory snapshot is 30 September 2026. '
        "Replenishment estimates calculate the working capital required to bring depleted positions "
        "back to reorder thresholds. Suggested order quantities reflect lead-time + 30-day demand planning aids."
        "</p>",
        unsafe_allow_html=True,
    )
    inv_stats = inventory_summary(filtered_inventory)
    action_statuses = ["Out of stock", "Stock-out risk", "Low stock"]
    needs_action = filtered_inventory.loc[filtered_inventory["stock_status"].isin(action_statuses)]

    cols1 = st.columns(3)
    cols1[0].metric(
        "Total Inventory Value",
        format_inr(inv_stats["total_inventory_value"]),
        help=f"Audited inventory value at cost: {format_exact_inr(inv_stats['total_inventory_value'])}",
    )
    cols1[1].metric(
        "True Out of Stock (0 units)",
        f"{inv_stats['stockout_positions']:,}",
        help="Stock positions with exactly 0 units on hand",
    )
    cols1[2].metric(
        "Positions Below Reorder Level",
        f"{inv_stats['below_reorder_positions']:,}",
        help="Stock positions where quantity on hand is below safety reorder threshold",
    )

    cols2 = st.columns(3)
    cols2[0].metric(
        "Replenishment Units Required",
        f"{inv_stats['replenishment_units_required']:,}",
        help="Total units required to restore depleted buffers to safety levels",
    )
    cols2[1].metric(
        "Replenishment Cost Estimate",
        format_inr(inv_stats["replenishment_cost_estimate"]),
        help=f"Audited working capital required at purchase cost: {format_exact_inr(inv_stats['replenishment_cost_estimate'])}",
    )
    cols2[2].metric(
        "Stock Gap Retail Valuation",
        format_inr(inv_stats["stock_gap_retail_val"]),
        help=f"Retail catalog list valuation of deficit units: {format_exact_inr(inv_stats['stock_gap_retail_val'])}",
    )

    st.markdown(
        '<div class="if-note" style="margin-top: 0.5rem; margin-bottom: 1rem;">'
        "<strong>Inventory Semantics Note:</strong> "
        "<strong>Replenishment Cost Estimate</strong> represents working capital required at purchase cost to restore buffer stock to safety reorder levels. "
        "<strong>Stock Gap Retail Valuation</strong> is the retail catalog list valuation of those deficit units (NOT confirmed lost revenue). "
        "<strong>Out of stock</strong> counts positions with exactly zero units on hand."
        "</div>",
        unsafe_allow_html=True,
    )
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
                "Out of stock": "#dc2626",
                "Stock-out risk": "#ea580c",
                "Low stock": "#d97706",
                "Overstocked": "#7c3aed",
                "Healthy": "#059669",
                "No recent sales": "#94a3b8",
            },
        )
        fig.update_traces(
            textposition="inside",
            textinfo="percent",
            hovertemplate="<b>%{label}</b><br>Positions: %{value:,}<br>Share: %{percent}<extra></extra>",
        )
        st.plotly_chart(
            style_chart(fig, 400, show_legend=True, legend_position="bottom"),
            use_container_width=True,
        )
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
            color_discrete_sequence=["#2563eb"],
        )
        fig.update_traces(hovertemplate="<b>%{y}</b><br>Inventory Value: ₹%{x:,.0f}<extra></extra>")
        st.plotly_chart(style_chart(fig, 400), use_container_width=True)

    st.subheader("Priority review queue")
    if not needs_action.empty:
        queue_filter = st.radio(
            "Filter queue by status:",
            options=[
                "All Actionable Positions",
                "Out of stock (0 units)",
                "Stock-out risk (< lead time)",
                "Low stock (<= reorder level)",
            ],
            horizontal=True,
            key="queue_status_filter",
        )
        priority = {"Out of stock": 1, "Stock-out risk": 2, "Low stock": 3}
        needs_action = needs_action.assign(_priority=needs_action["stock_status"].map(priority))
        needs_action = needs_action.sort_values(
            ["_priority", "suggested_order_qty"], ascending=[True, False]
        )

        filtered_queue = needs_action.copy()
        if queue_filter.startswith("Out of stock"):
            filtered_queue = filtered_queue.loc[filtered_queue["stock_status"] == "Out of stock"]
        elif queue_filter.startswith("Stock-out risk"):
            filtered_queue = filtered_queue.loc[filtered_queue["stock_status"] == "Stock-out risk"]
        elif queue_filter.startswith("Low stock"):
            filtered_queue = filtered_queue.loc[filtered_queue["stock_status"] == "Low stock"]

        display = filtered_queue.copy()
        display["Replenish cost (₹)"] = display["replenishment_cost_estimate"].map(
            lambda x: f"₹{x:,.2f}"
        )
        display["On hand"] = display["quantity_on_hand"].map(lambda x: f"{x:,}")
        display["Reorder level"] = display["reorder_level"].map(lambda x: f"{x:,}")
        display["Buffer deficit"] = display["replenishment_qty_required"].map(lambda x: f"{x:,}")
        display["Suggested order"] = display["suggested_order_qty"].map(lambda x: f"{x:,}")
        display["Avg units/day"] = display["avg_daily_units"].map(lambda x: f"{x:.2f}")
        display["Days of cover"] = display["days_of_cover"].map(
            lambda x: f"{x:.1f}" if pd.notnull(x) else "—"
        )
        display["Product"] = display["product_name"]
        display["Category"] = display["category_name"]
        display["Location"] = display["location_name"]
        status_badges = {
            "Out of stock": "🔴 Out of stock",
            "Stock-out risk": "🟠 Stock-out risk",
            "Low stock": "🟡 Low stock",
            "Healthy": "🟢 Healthy",
            "Overstocked": "🔵 Overstocked",
        }
        display["Status"] = display["stock_status"].map(lambda x: status_badges.get(x, x))

        table_cols = [
            "Product",
            "Category",
            "Location",
            "Status",
            "On hand",
            "Reorder level",
            "Buffer deficit",
            "Replenish cost (₹)",
            "Avg units/day",
            "Days of cover",
            "Suggested order",
        ]
        st.dataframe(display[table_cols], use_container_width=True, hide_index=True)
        st.download_button(
            "Download inventory review queue (CSV)",
            display[table_cols].to_csv(index=False).encode("utf-8"),
            file_name="insightflow_inventory_review.csv",
            mime="text/csv",
        )
    else:
        st.success("No inventory positions require action under the selected filters.")

else:
    st.markdown(
        """
        <div class="if-briefing">
          <div class="if-briefing-header">
            <span class="if-briefing-tag">Data Governance & Pipeline Assurance</span>
            <span class="if-briefing-date">Automated Quality Gateways & Reconciliation</span>
          </div>
          <p class="if-briefing-text">
            Ingestion pipeline profiled and validated <strong>49,975</strong> raw operational records across 8 sources.
            Through automated quality gates, <strong>47,814</strong> pristine records were loaded into the star schema
            (<strong>95.7% preservation rate</strong>), <strong>1,609</strong> anomalous rows were quarantined for audit, and
            <strong>512</strong> redundant duplicate records were eliminated. Customer analytics capture <strong>780</strong> active
            buying accounts with an <strong>82.6%</strong> repeat purchase rate.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
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

    st.markdown("### Pipeline Assurance & Reconciliation Balance")
    pa_cols = st.columns(5)
    pa_cols[0].metric(
        "Raw Ingested Records", "49,975", help="Audited total across all 8 source exports"
    )
    pa_cols[1].metric(
        "Clean Records Loaded", "47,814", help="Transformed & persisted into star schema"
    )
    pa_cols[2].metric("Preservation Rate", "95.7%", help="47,814 / 49,975 conservation efficiency")
    pa_cols[3].metric(
        "Quarantined Rows", "1,609", help="Anomalous records safely isolated with reason codes"
    )
    pa_cols[4].metric("Duplicates Dropped", "512", help="Identical duplicate records eliminated")

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
            color_discrete_sequence=["#2563eb"],
        )
        fig.update_traces(hovertemplate="<b>%{x}</b><br>Revenue: ₹%{y:,.0f}<extra></extra>")
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
            color_discrete_map={
                "Retail": "#2563eb",
                "Wholesale": "#0d9488",
                "Corporate": "#7c3aed",
            },
        )
        fig.update_traces(
            hovertemplate="<b>%{y}</b> (%{data.name})<br>Revenue: ₹%{x:,.0f}<extra></extra>"
        )
        st.plotly_chart(
            style_chart(fig, show_legend=True, legend_position="top-right"),
            use_container_width=True,
        )
    if defect_impact:
        st.subheader("Data Defect to Decision Impact Analysis")
        st.markdown(
            '<p class="if-section-note">Empirical comparison demonstrating how unvalidated source data '
            "distorts downstream business reporting, and how automated validation rules restore analytical ground truth.</p>",
            unsafe_allow_html=True,
        )

        st.markdown(
            """
            <div style="background: rgba(37, 99, 235, 0.05); border-left: 4px solid #2563eb; border-radius: 8px; padding: 12px 18px; margin-bottom: 1.25rem;">
              <div style="font-weight: 700; color: #1e40af; font-size: 0.92rem; margin-bottom: 4px;">
                Analytical Evidence: The Cost of Unvalidated ERP & CSV Exports
              </div>
              <div style="font-size: 0.86rem; color: #334155; line-height: 1.5;">
                Without validation gates, naive ERP line aggregation inflates turnover to <strong>₹429.93M (+105.7%)</strong> due to extreme quantity outliers and decimal errors;
                unverified invoice headers create an unaccounted <strong>₹5.72M</strong> variance; <strong>50 ghost customer accounts</strong> fracture ₹5.87M across secondary profiles;
                and <strong>18 missing reorder levels</strong> blind store operations to stockouts. InsightFlow resolves each defect deterministically.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        di_cols = st.columns(4)
        di_cols[0].metric(
            "Line Turnover Overstatement",
            "+105.7%",
            help="₹429.93M raw lines vs ₹209.03M validated (+₹220.90M distortion driven by 75 quantity outliers & 117 decimal shifts)",
        )
        di_cols[1].metric(
            "Invoice Header Variance",
            "₹5.72M",
            help="₹214.75M raw stated headers vs ₹209.03M validated lines (1,312 discrepant order totals & 107 duplicate orders)",
        )
        di_cols[2].metric(
            "Fractured Customer History",
            "₹5.87M Recovered",
            help="210 orders & ₹5.87M unified across 50 ghost duplicate profiles back into primary wholesale accounts",
        )
        di_cols[3].metric(
            "Restock Threshold Coverage",
            "100.0%",
            help="18 SKUs with NULL reorder levels imputed via median velocity, restoring automated replenishment triggers",
        )

        tab_sales, tab_cust, tab_inv, tab_trace = st.tabs(
            [
                "Sales Turnover & Line Distortion",
                "Customer Identity Fragmentation",
                "Inventory Replenishment Assurance",
                "Defect-to-Decision Traceability Matrix",
            ]
        )

        with tab_sales:
            st.markdown("**Sales Turnover Comparison (Population: FY 2025–26 Completed Orders)**")
            st.dataframe(defect_impact["sales_impact"], use_container_width=True, hide_index=True)
            st.caption(
                "Method note: Unvalidated Line Items calculates extended price directly from raw order_items without outlier caps. "
                "Unvalidated Headers sums stated order_total from raw orders. Validated Ground Truth enforces deduplication, outlier quarantine, and line-item cross-checking."
            )

        with tab_cust:
            st.markdown("**Customer Profile Fragmentation & Ghost Duplicate Accounts**")
            st.dataframe(
                defect_impact["customer_impact"], use_container_width=True, hide_index=True
            )
            st.markdown("**Top Commercial Accounts Fractured into Secondary IDs in Raw Data:**")
            st.dataframe(
                defect_impact["customer_top_fragmented"], use_container_width=True, hide_index=True
            )
            st.caption(
                "Method note: Duplicates identified via matching email or name+phone. 210 orders unified back to primary IDs, restoring true account purchasing tiers."
            )

        with tab_inv:
            st.markdown("**Inventory Threshold Coverage & Stockout Risk Prevention**")
            st.dataframe(
                defect_impact["inventory_impact"], use_container_width=True, hide_index=True
            )
            st.caption(
                "Method note: In unvalidated feeds, 18 inventory positions arrived with blank reorder levels, leaving replenishment alerts inactive. Category median imputation ensures zero blind spots."
            )

        with tab_trace:
            st.markdown("**End-to-End Defect-to-Decision Traceability Matrix**")
            st.dataframe(
                defect_impact["traceability_matrix"], use_container_width=True, hide_index=True
            )
            st.caption(
                "Audit trail links detected source volumes directly to pipeline control actions, downstream business risks, and validated operational resolutions."
            )

        st.markdown("---")

    st.subheader("Data quality actions")
    quality_display = (
        quality_log.sort_values("rows_affected", ascending=False)
        .rename(
            columns={
                "table_name": "Source table",
                "issue": "Issue detected",
                "rows_affected": "Rows affected",
                "action": "Action taken",
            }
        )
        .copy()
    )
    quality_display["Rows affected"] = quality_display["Rows affected"].map(lambda x: f"{x:,}")
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
    ).copy()
    missing_display["Source rows"] = missing_display["Source rows"].map(lambda x: f"{x:,}")
    missing_display["Missing cells"] = missing_display["Missing cells"].map(lambda x: f"{x:,}")
    missing_display["Distinct values"] = missing_display["Distinct values"].map(lambda x: f"{x:,}")
    missing_display["Missing (%)"] = missing_display["Missing (%)"].map(lambda x: f"{x:.1f}%")
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
