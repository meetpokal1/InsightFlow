import pathlib
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.demo import build_inventory_view, build_sales_lines  # noqa: E402
from src.config import PROJECT_ROOT  # noqa: E402
from src.pipeline import clean_raw_files  # noqa: E402

res = clean_raw_files(PROJECT_ROOT / "data" / "raw", date(2026, 9, 30))
sales_lines = build_sales_lines(res.clean)
inv_view = build_inventory_view(res.clean, sales_lines)

prod_perf = (
    sales_lines.groupby(["product_id", "product_name", "category_name"])
    .agg(
        units=("quantity", "sum"),
        net_rev=("net_revenue", "sum"),
        cogs=("cost_of_goods", "sum"),
        gross_profit=("gross_profit", "sum"),
    )
    .reset_index()
)

prod_perf["gross_margin_pct"] = (prod_perf["gross_profit"] / prod_perf["net_rev"] * 100).round(2)
prod_perf["rev_rank"] = prod_perf["net_rev"].rank(ascending=False, method="min").astype(int)
prod_perf["profit_rank"] = prod_perf["gross_profit"].rank(ascending=False, method="min").astype(int)

targets = ["P0010", "P0055", "P0006"]
filtered = prod_perf[prod_perf["product_id"].isin(targets)].sort_values("rev_rank")

print("=== TASK 1 INDEPENDENT RECALCULATION (FROM RAW PIPELINE) ===")
for _idx, row in filtered.iterrows():
    p_id = row["product_id"]
    p_name = row["product_name"]
    cat = row["category_name"]
    units = row["units"]
    rev = row["net_rev"]
    cogs = row["cogs"]
    gp = row["gross_profit"]
    gm = row["gross_margin_pct"]
    rr = row["rev_rank"]
    pr = row["profit_rank"]
    print(f"{p_id} | {p_name} ({cat})")
    print(f"  Units Sold: {units:,}")
    print(f"  Net Revenue: ₹{rev:,.2f} (Rank #{rr})")
    print(f"  COGS: ₹{cogs:,.2f}")
    print(f"  Gross Profit: ₹{gp:,.2f} (Rank #{pr})")
    print(f"  Gross Margin: {gm:.2f}%")

print("\n=== TOTAL PRODUCT COUNT ===")
print("Total distinct products in sales:", len(prod_perf))

print("\n=== INVENTORY REORDER & SHORTAGE ANALYSIS ===")
print("Inventory rows count:", len(inv_view))
print("Inventory columns:", inv_view.columns.tolist())
low_stock = inv_view[inv_view["stock_status"] == "Low Stock"]
out_of_stock = inv_view[inv_view["stock_status"] == "Out of Stock"]
adequate = inv_view[inv_view["stock_status"] == "Adequate"]
print(
    f"Status breakdown: Low Stock = {len(low_stock)}, Out of Stock = {len(out_of_stock)}, Adequate = {len(adequate)}"
)
print(f"Suggested reorder units sum: {inv_view['suggested_reorder_units'].sum():,}")
