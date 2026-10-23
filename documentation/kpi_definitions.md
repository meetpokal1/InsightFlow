# KPI definitions

Every KPI in the project is defined once here, with the place where it is calculated in SQL, in
the API and in Power BI. The three are meant to give the same number. Tests compare the SQL
views, the analytics queries and the API with an independent calculation in pandas, and the
expected Power BI values in [dax_measures.md](../powerbi/dax_measures.md) were calculated from
the same views.

The values are for the synthetic dataset in this repository: orders from 1 October 2024 to
30 September 2026 and one stock snapshot on 30 September 2026. Amounts are in rupees.

## Rules for every KPI

- **Only completed orders count.** Cancelled and returned orders are left out of every sales KPI
  (`vw_fact_sales`). They appear only in the order status KPIs at the end of this page.
- **Revenue is net of discounts.** Each line is `quantity * unit_price * (1 - discount_pct / 100)`.
  The data has no tax or shipping.
- **Cost is today's cost price.** Cost of goods is `quantity * cost_price` of the product. The
  data has no cost history, so the profit of old orders is only as exact as today's costs.
- **The last 12 months** are the 12 months that end on the last order date (30 September 2026).
  The **prior 12 months** are the 12 months before them.
- **Stock KPIs read one snapshot** (30 September 2026). They do not change with a date filter.

## Sales and profit

| KPI | Definition | SQL and API | Power BI | Value |
|---|---|---|---|---|
| Revenue | Sum of net revenue of completed order lines | `vw_fact_sales.net_revenue`; `/sales/summary` `total_revenue` | `[Revenue]` | 209.03M |
| Cost of goods | Sum of `quantity * cost_price` | `vw_fact_sales.cost_of_goods` | `[Cost of Goods]` | 166.68M |
| Gross profit | Revenue minus cost of goods | `vw_fact_sales.gross_profit`; `total_profit` | `[Gross Profit]` | 42.36M |
| Gross margin % | Gross profit divided by revenue | `margin_pct` | `[Gross Margin %]` | 20.3% |
| Orders | Number of distinct completed orders. Not the number of lines, because an order has several | `COUNT(DISTINCT order_id)`; `total_orders` | `[Orders]` | 7,878 |
| Units sold | Sum of `quantity` | `units_sold` | `[Units Sold]` | 1,111,322 |
| Average order value | Revenue divided by orders. Lines are added up to orders first, so it is not the average line | query 07; `avg_order_value` | `[Average Order Value]` | 26,534 |

The average order value differs a lot by customer type: wholesale 44,244, corporate 12,083 and
retail 2,703 (query 07).

## Growth

| KPI | Definition | SQL and API | Power BI | Value |
|---|---|---|---|---|
| Month on month growth | Revenue of a month divided by the revenue of the month before, minus 1 | query 02; `/sales/monthly` `mom_growth_pct` | `[Revenue MoM %]` | September 2026: -8.9% |
| Year on year growth | Revenue of a month divided by the revenue of the same month a year earlier, minus 1. First available for October 2025 | query 02 | `[Revenue YoY %]` | September 2026: +38.7% |
| Growth, last 12 months | Revenue of the last 12 months divided by the prior 12 months, minus 1. It does not depend on the date filter | query 05; `/analytics/category-performance` `growth_pct` (per category) | `[Revenue Growth Last 12 Months %]` | 47.2% |

Month on month growth moves between -21.6% and +55.9% in this data, so one month says little.
The 12 month growth is the steadier figure. Power BI also has `[Revenue PY]`, `[Revenue PM]` and
`[Revenue YTD]`, which are the building blocks of the growth measures and the year to date total.

## Products and categories

| KPI | Definition | SQL and API | Power BI | Value |
|---|---|---|---|---|
| Revenue share % | Revenue of a product, category or customer divided by the total of the current selection | query 03 (products), 04 (customers), 05 (categories); `/customers/top` `revenue_share_pct` | `[Revenue Share %]` | Basmati Rice 5kg: 7.9% |
| Product margin % | Gross profit divided by revenue of one product, with the real discounts | `/products/top` `margin_pct`; queries 03, 06 | `[Gross Margin %]` per product | Basmati Rice 5kg: 2.1% |
| Margin gap | Product margin minus the company margin, in points. Negative means the product earns less than average | query 06 | `[Margin Gap (pts)]` | Basmati Rice 5kg: -18.1 points |
| List margin % | `(selling_price - cost_price) / selling_price` at list price, before discounts | `vw_dim_product.list_margin_pct` | `Product[list_margin_pct]` | per product |
| Category share change | Change of a category's share of revenue between the prior and the last 12 months, in points | query 05; `share_change_pts` | not in the model | Electronics Accessories: +2.5 points |
| Category trend | Declining (revenue fell), Gaining share, Losing share or Steady | query 05; `trend` | not in the model | no category declined |
| Days of inventory | 365 divided by inventory turnover (see Inventory) | query 09 | `[Days of Inventory]` | 83 days |

Almost every category grows in absolute terms, because the whole business grows by 47%. That is
why the trend also looks at the change of share.

## Customers

| KPI | Definition | SQL and API | Power BI | Value |
|---|---|---|---|---|
| Active customers | Customers with at least one completed order in the selection | `COUNT(DISTINCT customer_id)`; `total_customers` | `[Active Customers]` | 780 of 800 |
| Revenue per customer | Revenue divided by active customers | | `[Revenue per Customer]` | 267,993 |
| Orders per customer | Orders divided by active customers | | `[Orders per Customer]` | 10.1 |
| Repeat customer rate | Customers with two or more orders divided by active customers | query 08 | `[Repeat Customer Rate %]` | 82.6% (644 customers) |
| Top 10 customers' share | Revenue of the 10 largest customers divided by all revenue | query 04; `/customers/top` | `[Top 10 Customers Revenue Share %]` | 20.05% |
| New customers | Customers whose first completed order falls in the period | `vw_dim_customer.first_order_date` | `[New Customers]` | September 2026: 3 |
| RFM segment | Champions, Regular, New or one-time, At risk or Lost, from recency, frequency and monetary scores. The rules are in [database_schema.md](database_schema.md#vw_customer_segments) | `vw_customer_segments`; query 13 | `Customer[segment]`, `[Customers]` | Champions 311, At risk 111, Lost 173 |

The repeat rate in Power BI counts orders inside the selection. With a date filter it is
therefore not the all-time figure of query 08.

## Inventory

| KPI | Definition | SQL and API | Power BI | Value |
|---|---|---|---|---|
| Stock value | Sum of `quantity_on_hand * cost_price` | `vw_fact_inventory.inventory_value`; `/sales/summary` `inventory_value` | `[Stock Value]` | 22.49M |
| Stock position | One product at one location in the snapshot | `COUNT(*)` of `vw_fact_inventory` | `[Stock Positions]` | 449 |
| Days of cover | `quantity_on_hand * 90 / units_sold_90d`: how long the stock lasts at the sales rate of the last 90 days. Empty when nothing sold | `vw_fact_inventory.days_of_cover`; `/inventory/low-stock` | `[Days of Cover]` | 81.2 days |
| Stock status | The first matching rule of: No recent sales, Out of stock, Stock-out risk (cover below the supplier lead time), Low stock (at or below the reorder level), Overstocked (more than 180 days of cover), Healthy | `vw_fact_inventory.stock_status` | `Inventory[stock_status]` | 20, 39, 39, 14, 45 and 292 positions |
| Items needing action | Out of stock, Stock-out risk and Low stock positions together | query 11; `/inventory/low-stock` | `[Items Needing Action]` | 92 |
| Replenishment quantity required | `GREATEST(reorder_level - quantity_on_hand, 0)`: units required to bring depleted positions back to safety reorder threshold | `vw_fact_inventory.replenishment_quantity_required` | `[Replenishment Qty Required]` | 5,791 units across 96 positions |
| Replenishment cost estimate | `replenishment_quantity_required * cost_price`: working capital required at purchase cost to restore buffer to reorder level | `vw_fact_inventory.replenishment_cost_estimate` | `[Replenishment Cost Estimate]` | ₹9.66 L (₹966,026.68) |
| Stock gap retail valuation | `replenishment_quantity_required * selling_price`: retail catalog valuation of the buffer deficit units | `vw_fact_inventory.stock_gap_retail_valuation` | `[Stock Gap Retail Valuation]` | ₹13.41 L (₹1,340,814.00) |
| True zero-stock exposure | Positions with strictly `quantity_on_hand == 0` | `vw_fact_inventory.is_stockout` | `[Stockout Positions]` | 40 positions |
| Overstock share | Cost value of overstocked positions divided by stock value | query 16 | `[Overstock Share of Stock %]` | 56.4% (12.69M) |
| Suggested order quantity | `CEIL(avg_daily_units * (lead_time_days + 30)) - quantity_on_hand`, never below 0. The units that cover the lead time plus 30 days of sales | `vw_fact_inventory.suggested_order_qty`; `suggested_order_qty` | `[Suggested Order Units]` | 15,641 units in total |
| Inventory turnover | Cost of goods of the last 12 months divided by stock value | query 09 | `[Inventory Turnover]` | 4.41 a year |

> [!IMPORTANT]
> **Inventory Semantics Distinction:**
> - **Replenishment Cost Estimate (₹9.66 L):** The actual purchase capital required to restore safety buffer stock up to reorder level.
> - **Stock Gap Retail Valuation (₹13.41 L):** The potential selling price of those replenishment units. This is a catalog valuation, **not confirmed lost sales**.
> - **True Out of Stock vs Low Stock:** 40 positions have 0 units on hand (immediate fulfillment failure risk), whereas 56 positions have stock above 0 but below the reorder threshold (depleted buffer risk).
> - Never label stock buffer gaps as "lost revenue" unless unfulfilled customer orders or bounce transactions can be directly measured.

Turnover and days of inventory use the single snapshot instead of an average stock. With one
snapshot per month, the average of the year would be the better base.

## Order status (SQL only)

These need the cancelled and returned orders, which are not in the sales views or in the Power
BI model. Query 17 reads the `orders` table directly.

| KPI | Definition | Value |
|---|---|---|
| Cancellation rate | Cancelled orders divided by all orders | 6.1% (529 of 8,734) |
| Return rate | Returned orders divided by all orders | 3.7% (327 of 8,734) |
| Value not counted as revenue | Net value of the lines of cancelled and returned orders | 24.08M |

## Data quality

How much of the raw data was repaired, rejected or lost is described in
[data_quality.md](data_quality.md). The counts per problem are in `data_quality_report.csv` and
in the `etl_quality_log` table.
