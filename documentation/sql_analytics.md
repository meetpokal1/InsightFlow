# SQL analytics

The 17 queries are in `sql/analytics/`. Each file starts with the business question and a short
comment on why the SQL technique is the right one. They read the views described in
[database_schema.md](database_schema.md), except where a comment says otherwise.

```bash
python scripts/run_analytics.py                  # run all, print the first rows
python scripts/run_analytics.py --only 05 11     # run some of them
python scripts/run_analytics.py --export         # also write CSVs to data/processed/analytics
```

You can also run a file directly: `psql -U sales_user -d sales_intelligence -f sql/analytics/05_category_performance.sql`.

The results quoted below come from the synthetic dataset in this repository (24 months of
orders, October 2024 to September 2026). They show what each query returns; they are not
findings about a real business.

## Where each SQL technique is used

| Technique | Used in |
|---|---|
| SELECT, WHERE, JOIN | all queries; WHERE for example in 11, 15 and 16 |
| GROUP BY | 01, 03, 05, 12, 13, 17 and most others |
| HAVING | 06 |
| CASE | 05, 10, 11, and `vw_customer_segments` and `vw_fact_inventory` |
| Subqueries | 06 (inside `HAVING`), 09, 10 and 15 (scalar subqueries), 16 (`NOT EXISTS`) |
| CTEs | 02, 04 to 10, 14 to 17 |
| Window functions | `LAG` 02, 15; `RANK` 03, 12, 14; running total 04; `NTILE` 10; share of total 03, 04, 05, 13 |
| Aggregate `FILTER`, `ROLLUP` | `FILTER` 05, 08, 17; `ROLLUP` 07, 08, 09, 17 |
| `UNION ALL` | 16 |
| `generate_series`, `CROSS JOIN`, `COALESCE` | 02, 15 |

## The queries

| # | File | Question |
|---|---|---|
| 01 | monthly_revenue | How much do we sell each month, and how profitable is it? |
| 02 | monthly_growth | Is revenue growing, month on month and year on year? |
| 03 | top_products | Which products bring in the most revenue, and the most profit? |
| 04 | top_customers | Which customers matter most, and how concentrated is revenue? |
| 05 | category_performance | Which categories earn the most and which are gaining or losing share? |
| 06 | profit_margins | Which big sellers earn a thin margin? |
| 07 | average_order_value | What is the average order value by customer type? |
| 08 | repeat_customers | What share of customers order again? |
| 09 | inventory_turnover | How quickly does stock turn into sales? |
| 10 | slow_moving_products | Which products sit in stock the longest compared with their sales? |
| 11 | low_stock_products | What is about to run out, and how much should be ordered? |
| 12 | regional_performance | Which regions and locations perform best? |
| 13 | customer_segmentation | Which customer groups exist and how much does each one matter? |
| 14 | product_ranking | What are the best sellers inside each category? |
| 15 | month_over_month_comparison | How did each category do in the last 6 months? |
| 16 | inventory_sales_mismatch | Where do inventory and sales disagree? |
| 17 | order_status_mix | How many orders are cancelled or returned, and what does it cost? |

### 01 Monthly revenue

`GROUP BY date_trunc('month', order_date)` turns order lines into months. Orders are counted
with `COUNT(DISTINCT order_id)` because an order has several lines, and `COUNT(*)` would count
lines.

Result: 24 rows. The margin stays between 18.6% and 22.0% in every month. The month with the
lowest revenue is February 2025 (₹5.09M, 198 orders) and the highest is March 2026 (₹12.21M,
424 orders).

### 02 Monthly growth

A CTE reduces the data to one revenue figure per month, then `LAG(revenue)` reads the previous
month and `LAG(revenue, 12)` the same month a year earlier. `LAG` needs no self-join, but it
counts rows and not months. `generate_series` therefore lists every month between the first and
the last order, and a left join gives a month without sales a revenue of 0. Without it the month
after a gap would be compared with the month before the gap. A test removes the sales of one
month and checks this. No month is missing in this dataset, so the result is the same either
way. `NULLIF` avoids division by zero.

Result: month on month swings from -21.6% to +55.9%, so a single month says little. Year on
year growth, available from October 2025, is between 16.5% (May 2026) and 85.6% (July 2026).
September 2026 is -8.9% on August and +38.7% on September 2025.

### 03 Top products

Two `RANK()` windows over the grouped result put the revenue rank and the profit rank side by
side. `SUM(SUM(net_revenue)) OVER ()` is the grand total inside the same query, used for the
revenue share.

Result: Basmati Rice 5kg is first by revenue (₹16.47M, 7.9% of all revenue) and 39th by profit,
because its margin is 2.1%. The most profitable product is the Wireless Mouse (₹2.98M profit,
25.8% margin).

### 04 Top customers

A CTE totals revenue per customer. A window `SUM` with an explicit frame
(`ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`) gives the running total in rank order,
which is the cumulative share. Spelling out the frame keeps customers with equal revenue from
being added in a single step.

Result: the largest customer, Bhatt Stores, is 2.77% of revenue. The top 10 customers are 20.05%
and the top 20 are 32.78%. All 20 are wholesale accounts.

### 05 Category performance

`SUM(...) FILTER (WHERE ...)` puts the last 12 months next to the 12 months before in one pass.
The last sales date is read from the data, so no date is written into the query, and a year is
12 calendar months back from that date (the same definition as the Power BI measures).
Because the whole business grows, almost every category grows in absolute terms, so the trend
label also uses the change of each category's revenue share in percentage points.

Result: Electronics Accessories is 23.9% of revenue in the last 12 months, grew 64.1% and gained
2.5 points of share. Stationery & Office grew 29.9% but lost 1.1 points. No category declined in
absolute terms.

### 06 Profit margins

"Sells a lot" and "thin margin" both depend on totals per product, so they go in `HAVING`
(`WHERE` runs before the grouping and cannot see totals). The median product revenue comes from
a subquery with `percentile_cont`, the company margin from a CTE.

Result: 13 products sell at least the median revenue with a margin below the company's 20.3%.
Basmati Rice 5kg (2.1% margin) alone would add ₹2.98M of profit at the company margin.
Mineral Water 1L (12 Pack) is the next with the same 2.1% margin.

### 07 Average order value

The lines are first added to one value per order in a CTE, because averaging lines would give
the average line. `GROUP BY ROLLUP` adds an "All customers" row. The median is shown next to the
mean because a few very large orders pull the mean up.

Result: wholesale ₹44,244 (median ₹40,725), corporate ₹12,083, retail ₹2,703 with a median of
only ₹927. The retail mean is about three times its median, so a few large retail orders
distort it. All customers: ₹26,534.

### 08 Repeat customers

The CTE counts orders per customer. `COUNT(*) FILTER (WHERE orders >= 2)` counts the repeat
customers in the same `GROUP BY`.

Result: 644 of 780 customers (82.6%) ordered at least twice. Wholesale is 100% (136 customers, 31.9
orders each on average), corporate 90.9% and retail 77.2%.

### 09 Inventory turnover

Turnover is cost of goods sold in the last 12 months divided by stock value, and days of
inventory is 365 divided by turnover. Sales and stock are totalled per category in separate CTEs
before they are joined; joining the raw rows first would repeat each stock row once per sale
and inflate the totals. There is only one stock snapshot, so it stands in for the average
stock. With monthly snapshots the average of 12 values would be the better base.

Result: 4.41 turns a year overall (83 days of inventory). Packaged Foods turns fastest (7.50,
49 days), Electronics Accessories slowest (2.90, 126 days).

### 10 Slow moving products

Slow means days of cover (units in stock divided by the daily sales of the last 90 days), not
units sold. `NTILE(4)` cuts the 60 products into four equal groups by cover and the slowest
group is kept. A window function cannot be filtered in `WHERE` of the same query, so the ranking
is in a CTE and the filter is on its result. Products with no sales have no cover (`NULL`) and
sort first, on purpose.

Result: 15 products, holding ₹10.94M of the ₹22.49M stock value. The largest are the Wireless
Mouse (₹3.38M, 207 days of cover) and the Bluetooth Earbuds (₹2.11M, 129 days). All 15 still
sold something in the last 90 days, so none is dead stock.

### 11 Low stock products

The status comes from `vw_fact_inventory`: out of stock, stock that will run out before the
supplier lead time has passed, or at the reorder level. The `CASE` in `ORDER BY` puts the most
urgent first, then the items with the highest sales per day. The suggested quantity covers the
lead time plus 30 days of sales.

Result: 92 product and location pairs (39 out of stock, 39 at risk, 14 low). The first is
Bluetooth Earbuds at Pune Store, out of stock with about ₹2,683 of sales per day at list price
and a suggested order of 92 units.

### 12 Regional performance

One `GROUP BY` at location level gives every measure. Two `RANK()` windows run over the grouped
rows, one across the company and one `PARTITION BY region`, so a location can be compared with
all others and with its regional peers.

Result: Mumbai Warehouse (₹43.73M) and Bengaluru Warehouse (₹43.72M) are each 20.9% of revenue.
Chennai Store is the smallest (₹11.86M, 5.7%). Margins are close everywhere, between 19.9% and
20.7%.

### 13 Customer segmentation

The RFM segments are calculated once in `vw_customer_segments` (see
[database_schema.md](database_schema.md#vw_customer_segments)). This query adds customers up per
segment, with `SUM() OVER ()` for each segment's share of the whole.

Result: Champions are 311 customers (39.9%) and 95.6% of revenue. The 173 Lost customers
(22.2%) are 0.3% of revenue and last ordered 380 days before the end of the data on average. The
111 At risk customers (14.2%) have averaged 7.6 orders and last ordered 154 days before the end
of the data.

### 14 Product ranking

`RANK() OVER (PARTITION BY category_name ...)` restarts the ranking in every category, and
`SUM() OVER (PARTITION BY ...)` gives each product's share of its category without collapsing
rows. The ranking is in a CTE so the outer query can keep the top 3 per category.

Result: Basmati Rice is 54.9% of Packaged Foods revenue. In Electronics Accessories the top
three products are almost equal (25.4%, 24.1%, 23.3%).

### 15 Month over month comparison

`LAG(revenue) OVER (PARTITION BY category_name ORDER BY month)` looks back inside one category.
As in query 02, every category is paired with every month first (`CROSS JOIN`), so a category
without sales in a month keeps its row. The change is calculated for all months and the last 6
are kept afterwards, because filtering first would remove the earlier rows `LAG` needs.

Result: 48 rows, 8 categories times 6 months, with the change against the previous month and
against the same month a year earlier.

### 16 Inventory and sales mismatch

Four kinds of mismatch, stacked with `UNION ALL` so they can be compared. "Sold, but no stock
record" uses `NOT EXISTS`, which keeps the sales rows that have no match in `inventory`.

| Mismatch | Product and location pairs | Value |
|---|---|---|
| Sold, but no stock record | 30 | ₹1.69M revenue in the last 90 days |
| In stock, nothing sold in 90 days | 19 | ₹0.49M cost value of the stock |
| Selling, but out of stock | 39 | ₹2.42M of sales in the last 90 days, at list price |
| Overstocked (over 180 days of cover) | 45 | ₹12.69M cost value of the stock |

The overstocked pairs hold 56% of the ₹22.49M stock value.

### 17 Order status mix

Cancelled and returned orders are not in the sales views, so this query reads the `orders`
table directly. `COUNT(*) FILTER (WHERE ...)` counts each status in one pass, order values come
from a CTE so an order is counted once, and `ROLLUP` adds the company total.

Result: of 8,734 orders, 529 were cancelled (6.1%) and 327 returned (3.7%). Their value, about
₹24.08M, is not counted as revenue. The cancelled share is between 5.0% (Jaipur Store) and 7.1%
(Chennai Store).
