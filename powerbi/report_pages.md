# Report pages

Four pages, each answering one question. The report pages and semantic model are fully authored in
`InsightFlow.pbip` ([README.md](README.md), [dax_measures.md](dax_measures.md)), with verified runtime
captures saved in `screenshots/powerbi/`.

## Rules for every page

- Page size 16:9 (1280 x 720). Apply `theme.json` (View > Themes > Browse for themes).
- One strip of slicers along the top, KPI cards under it, charts below. Page navigation buttons
  (Insert > Buttons > Navigator > Page navigator) at the left or top.
- Every visual has a title that says what it shows ("Revenue by month", not "Chart 1").
- One axis per chart. Two measures of different size go in two charts, never on a second axis.
  Revenue and the same month last year share a unit, so they can share a chart.
- A single series needs no legend. Two or more get one. Bars start at zero and are sorted by
  value unless the order has a meaning (months, stock status).
- Put data labels on bars. They also keep the lighter theme colours readable. Every chart can be
  shown as a table (visual menu > Show as a table).
- Do not use pie or donut charts. The stock status colours (listed in [README.md](README.md))
  are only for stock status and other warnings, never for ordinary categories.
- Use **Edit interactions** where a visual should not react to another one (noted below).

## Page 1: Executive Overview

*How is the business doing, and what needs attention?*

**Slicers.** Date (between, `Date[date_key]`), Region (`Location[region]`), Customer type
(`Customer[customer_type]`), Category (`Product[category_name]`).

**Cards.**

| Card | Measure |
|---|---|
| Revenue | `[Revenue]`, display units millions |
| Gross profit | `[Gross Profit]` |
| Gross margin | `[Gross Margin %]` |
| Orders | `[Orders]` |
| Average order value | `[Average Order Value]` |
| Active customers | `[Active Customers]` |
| Growth, last 12 months | `[Revenue Growth Last 12 Months %]` (ignores the date slicer) |
| Items needing action | `[Items Needing Action]` (stock, ignores the date and customer type slicers) |

**Charts.**

| Visual | Fields | Notes |
|---|---|---|
| Line chart, "Revenue by month" | axis `Date[year_month]`, values `[Revenue]` and `[Revenue PY]` | the second line is the same month last year, set to grey `#898781` and dashed so it reads as the comparison; tooltips `[Revenue YoY %]`, `[Revenue MoM %]`, `[Gross Margin %]` |
| Bar chart, "Revenue by location" | axis `Location[location_name]`, value `[Revenue]` | sorted descending, data labels |
| Bar chart, "Revenue by category" | axis `Product[category_name]`, value `[Revenue]` | sorted descending, data labels |
| Table, "Top 5 products" | `Product[product_name]`, `[Revenue]`, `[Gross Margin %]`, `[Revenue Share %]` | visual filter: Top N 5 by `[Revenue]` |

**What to expect with no slicers:** revenue 209.0M, profit 42.4M, margin 20.3%, 7,878 orders,
average order 26,534, 780 active customers, growth 47.2%, 92 items needing action. Basmati Rice
5kg is the largest product by revenue (16.5M) with a margin of 2.1%.

## Page 2: Sales Analysis

*Where does revenue come from, and how good is the margin?*

**Slicers.** Date, Location (`Location[location_name]`, dropdown), Customer type, Category.

| Visual | Fields | Notes |
|---|---|---|
| Column chart, "Revenue by month" | axis `Date[year_month]`, value `[Revenue]` | |
| Line chart, "Gross margin by month" | axis `Date[year_month]`, value `[Gross Margin %]` | set the value axis from 15% to 25% and say so in the title, because the margin moves in a narrow band |
| Bar chart, "Revenue by customer type" | axis `Customer[customer_type]`, value `[Revenue]` | wholesale is 91.8% of revenue |
| Bar chart, "Average order value by customer type" | axis `Customer[customer_type]`, value `[Average Order Value]` | matches `sql/analytics/07` |
| Scatter chart, "Revenue and margin by product" | x `[Revenue]`, y `[Gross Margin %]`, details `Product[product_name]` | one colour; add a constant line on y at `[Company Gross Margin %]` (Analytics pane, fx); tooltips `[Units Sold]`, `Product[category_name]`. Products in the lower right sell a lot with a thin margin |
| Matrix, "Product margins" | rows `Product[category_name]` then `Product[product_name]`; values `[Revenue]` (data bars), `[Revenue Share %]`, `[Gross Profit]`, `[Gross Margin %]` | conditional formatting on `[Gross Margin %]`: icon rule on `[Margin Gap (pts)]`, a warning icon when below 0 |

Check: the product rows match `sql/analytics/03_top_products.sql` and `06_profit_margins.sql`.

## Page 3: Inventory Intelligence

*What will run out, what is stuck, and what should be ordered?*

**Slicers.** Region and Location (`Location[region]`, `Location[location_name]`), Category
(`Product[category_name]`), Stock status (`Inventory[stock_status]`).
**No date slicer.** Stock is one snapshot, and `Date` is not related to `Inventory`.

**Cards.** `[Stock Value]`, `[Items Needing Action]`, `[Out of Stock Items]`,
`[Overstock Value]` with `[Overstock Share of Stock %]` in the subtitle, `[Days of Inventory]`.

| Visual | Fields | Notes |
|---|---|---|
| Bar chart, "Stock positions by status" | axis `Inventory[stock_status]` (sorted by `Status Order`), value `[Stock Positions]` | set the bar colours by hand: Out of stock red `#D03B3B`, Stock-out risk orange `#EC835A`, Low stock yellow `#FAB219`, Overstocked blue `#2A78D6`, Healthy green `#0CA30C`, No recent sales grey `#898781`; data labels on |
| Stacked bar, "Stock status by location" | axis `Location[location_name]`, legend `Inventory[stock_status]`, value `[Stock Positions]` | same status colours, legend on |
| Bar chart, "Days of inventory by category" | axis `Product[category_name]`, value `[Days of Inventory]` | sorted descending; matches `sql/analytics/09` |
| Bar chart, "Stock value by category" | axis `Product[category_name]`, value `[Stock Value]` | |
| Table, "Reorder list" | `Product[product_name]`, `Location[location_name]`, `Inventory[quantity_on_hand]`, `Inventory[reorder_level]`, `Inventory[days_of_cover]`, `Inventory[lead_time_days]`, `Inventory[stock_status]`, `Inventory[suggested_order_qty]` | visual filter: `stock_status` is Out of stock, Stock-out risk or Low stock; sort by `suggested_order_qty` descending; the status text stays visible next to its colour |

**What to expect with no slicers:** 449 stock positions, stock value 22.49M, 39 out of stock,
39 at risk, 14 low (92 items needing action), 45 overstocked holding 12.69M (56.4% of the
stock value), 83 days of inventory. The reorder list has 92 rows, the same as
`sql/analytics/11_low_stock_products.sql`.

## Page 4: Customer Analysis

*Who are our customers, and who is slipping away?*

**Slicers.** Date, Customer type (`Customer[customer_type]`), City (`Customer[city]`, dropdown),
Segment (`Customer[segment]`).

**Cards.** `[Active Customers]`, `[Repeat Customer Rate %]`, `[Revenue per Customer]`,
`[Orders per Customer]`, `[Top 10 Customers Revenue Share %]`, `[New Customers]`.

| Visual | Fields | Notes |
|---|---|---|
| Matrix, "Customer segments" | rows `Customer[segment]` (sorted by `Segment Order`); values `[Customers]`, `[Customer Share %]`, `[Revenue]`, `[Revenue Share %]`, `[Orders per Customer]` | Champions are 311 customers and 95.6% of revenue |
| Column chart, "New customers by month" | axis `Date[year_month]`, value `[New Customers]` | |
| Line chart, "Active customers by month" | axis `Date[year_month]`, value `[Active Customers]` | |
| Table, "Top 10 customers" | `Customer[customer_name]`, `Customer[customer_type]`, `Customer[city]`, `[Orders]`, `[Revenue]`, `[Revenue Share %]`, `Customer[last_order_date]` | visual filter: Top N 10 by `[Revenue]` |
| Table, "At risk: win back" | `Customer[customer_name]`, `Customer[city]`, `Customer[customer_type]`, `Customer[last_order_date]`, `[Orders]`, `[Revenue]` | visual filter: `segment` is At risk (111 customers) |

Selecting a segment in the matrix filters the two tables, which is the intent. Switch the
matrix off from the cards with **Edit interactions** so the cards keep showing all customers.

## Checking a finished page

1. With no slicer selected, every card should equal the numbers above and in
   [dax_measures.md](dax_measures.md).
2. Select one location. The total of the location bar chart on page 1 must still equal the
   revenue card.
3. Select one month. `[Revenue MoM %]` in the tooltip of the monthly chart is the change against
   the month before.
4. Export or capture each finished page and verify against the baseline captures in
   `screenshots/powerbi/` under the corresponding page name.
