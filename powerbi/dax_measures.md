# DAX measures

This reference documents 44 DAX measure definitions and 2 calculated columns. The checked-in PBIP model currently implements 24 numeric measures plus 3 text-only card display measures; other definitions in this catalog are available for extending the report. The names below assume the tables from
[README.md](README.md): `Sales`, `Inventory`, `Date`, `Product`, `Customer` and `Location`.

The analytical measures were written for Power BI Desktop and could not be run in the
environment where this project was built, because Power BI Desktop only runs on Windows. Each
numeric analytical measure has an expected value calculated in PostgreSQL from the same views, so
you can check it after you create it ([Checking the measures](#checking-the-measures)). The
three card-only currency display measures are text labels and are intentionally excluded from the
numeric benchmark table.

Create a measure with **Home > New measure** (or right-click a table > New measure) and paste
the code. Keeping them all in the `Sales` table is fine. In the Model view, a *display folder*
for each group below keeps the field list tidy. `Date` is written with quotes
(`'Date'[date_key]`) so it is not confused with the `DATE` function.

Suggested formats: money `"₹"#,0`, percentages `0.0%`, counts `#,0`.

## Set up the model first

1. **Date table.** Select the `Date` table, then **Table tools > Mark as date table** and pick
   `date_key`. Time intelligence only works on a marked date table. In *File > Options >
   Current file > Data load*, turn off *Auto date/time*.
2. **Sort columns.** `Date[month_name]` sorted by `month_number`, `Date[day_name]` sorted by
   `day_of_week`. (Select the column, **Column tools > Sort by column**.)
3. **Calculated columns.** They give the status and the segment a sensible order in charts
   (worst first) instead of alphabetical order. Create them with **New column**, then use
   **Sort by column** on `stock_status` and `segment`.

```dax
Status Order =
SWITCH(
    Inventory[stock_status],
    "Out of stock", 1,
    "Stock-out risk", 2,
    "Low stock", 3,
    "Overstocked", 4,
    "Healthy", 5,
    6
)
```

```dax
Segment Order =
SWITCH(
    Customer[segment],
    "Champions", 1,
    "Regular", 2,
    "New or one-time", 3,
    "At risk", 4,
    "Lost", 5,
    6
)
```

## Sales

Folder `Sales`. These match `vw_fact_sales`, so they only count completed orders.

```dax
Revenue = SUM(Sales[net_revenue])
```

```dax
Cost of Goods = SUM(Sales[cost_of_goods])
```

```dax
Gross Profit = SUM(Sales[gross_profit])
```

```dax
Gross Margin % = DIVIDE([Gross Profit], [Revenue])
```

```dax
Orders = DISTINCTCOUNT(Sales[order_id])
```

`COUNTROWS(Sales)` would count order lines. An order has several lines.

```dax
Units Sold = SUM(Sales[quantity])
```

```dax
Average Order Value = DIVIDE([Revenue], [Orders])
```

## Time

Folder `Time`. The comparison measures need a month or a year in the filter context, for
example a month on a chart axis. For a whole selection of 18 months, "same period last year"
means nothing, so `Revenue YoY %` and `Revenue MoM %` return blank when the selection is
longer than a year or a month. `[Days Selected]` is what they test.

```dax
Days Selected = DATEDIFF(MIN('Date'[date_key]), MAX('Date'[date_key]), DAY) + 1
```

```dax
Revenue PY = CALCULATE([Revenue], SAMEPERIODLASTYEAR('Date'[date_key]))
```

```dax
Revenue YoY % =
IF(
    [Days Selected] <= 366,
    DIVIDE([Revenue] - [Revenue PY], [Revenue PY])
)
```

```dax
Revenue PM = CALCULATE([Revenue], DATEADD('Date'[date_key], -1, MONTH))
```

```dax
Revenue MoM % =
IF(
    [Days Selected] <= 31,
    DIVIDE([Revenue] - [Revenue PM], [Revenue PM])
)
```

```dax
Revenue YTD = TOTALYTD([Revenue], 'Date'[date_key])
```

The next four measures do not depend on the date selection. They always look at the 12 months
that end on the last day with a sale, the same period as `sql/analytics/05_category_performance.sql`.
That gives the report a growth figure that stays meaningful in a card.

```dax
Last Sales Date = CALCULATE(MAX(Sales[order_date]), REMOVEFILTERS())
```

```dax
Revenue Last 12 Months =
CALCULATE(
    [Revenue],
    DATESINPERIOD('Date'[date_key], [Last Sales Date], -12, MONTH)
)
```

```dax
Revenue Prior 12 Months =
CALCULATE(
    [Revenue],
    DATESINPERIOD('Date'[date_key], EDATE([Last Sales Date], -12), -12, MONTH)
)
```

```dax
Revenue Growth Last 12 Months % =
DIVIDE([Revenue Last 12 Months] - [Revenue Prior 12 Months], [Revenue Prior 12 Months])
```

## Products

Folder `Products`.

```dax
Revenue Share % = DIVIDE([Revenue], CALCULATE([Revenue], ALLSELECTED()))
```

The share of the total of whatever is currently selected by the slicers, so the bars of a chart
add up to 100%.

```dax
Company Gross Margin % = CALCULATE([Gross Margin %], REMOVEFILTERS(Product))
```

```dax
Margin Gap (pts) = ([Gross Margin %] - [Company Gross Margin %]) * 100
```

A product with a negative gap earns less than the average product. Used for the warning icon in
the product table.

## Customers

Folder `Customers`.

```dax
Active Customers = DISTINCTCOUNT(Sales[customer_id])
```

Customers with at least one completed order in the selection.

```dax
Customers = COUNTROWS(Customer)
```

All customers in the `Customer` table, including the 20 who never bought anything. Use it with
`Customer[segment]` on an axis.

```dax
Customer Share % = DIVIDE([Customers], CALCULATE([Customers], ALLSELECTED()))
```

Each segment's share of all customers shown. It counts the 20 customers without purchases too, so
the shares are out of 800 and differ a little from `sql/analytics/13_customer_segmentation.sql`,
which only looks at the 780 customers who bought.

```dax
Revenue per Customer = DIVIDE([Revenue], [Active Customers])
```

```dax
Orders per Customer = DIVIDE([Orders], [Active Customers])
```

```dax
Repeat Customers =
COUNTROWS(
    FILTER(
        VALUES(Sales[customer_id]),
        CALCULATE(DISTINCTCOUNT(Sales[order_id])) >= 2
    )
)
```

Customers with two or more orders **in the selection**. With a date slicer this is therefore
not the same as the all-time figure of `sql/analytics/08_repeat_customers.sql`.

```dax
Repeat Customer Rate % = DIVIDE([Repeat Customers], [Active Customers])
```

```dax
New Customers =
VAR period_start = MIN('Date'[date_key])
VAR period_end = MAX('Date'[date_key])
RETURN
    CALCULATE(
        COUNTROWS(Customer),
        Customer[first_order_date] >= period_start,
        Customer[first_order_date] <= period_end
    )
```

Customers whose first order falls in the period. The `Customer` table is not filtered by
`Location` or `Product`, so those slicers do not change this measure.

```dax
Top 10 Customers Revenue Share % =
VAR top_customers = TOPN(10, ALLSELECTED(Customer[customer_id]), [Revenue], DESC)
RETURN
    DIVIDE(
        CALCULATE([Revenue], top_customers),
        CALCULATE([Revenue], ALLSELECTED(Customer))
    )
```

## Inventory

Folder `Inventory`. Stock is a single snapshot, so these ignore the date slicer. The
`Inventory` table is related to `Product` and `Location` only.

```dax
Stock Value = SUM(Inventory[inventory_value])
```

```dax
Units on Hand = SUM(Inventory[quantity_on_hand])
```

```dax
Stock Positions = COUNTROWS(Inventory)
```

One position is one product at one location.

```dax
Out of Stock Items =
CALCULATE(COUNTROWS(Inventory), Inventory[stock_status] = "Out of stock") + 0
```

```dax
Stock-out Risk Items =
CALCULATE(COUNTROWS(Inventory), Inventory[stock_status] = "Stock-out risk") + 0
```

```dax
Low Stock Items =
CALCULATE(COUNTROWS(Inventory), Inventory[stock_status] = "Low stock") + 0
```

```dax
Items Needing Action = [Out of Stock Items] + [Stock-out Risk Items] + [Low Stock Items]
```

The `+ 0` makes the count show 0 instead of blank when nothing matches.

```dax
Overstocked Items =
CALCULATE(COUNTROWS(Inventory), Inventory[stock_status] = "Overstocked") + 0
```

```dax
Overstock Value = CALCULATE([Stock Value], Inventory[stock_status] = "Overstocked")
```

```dax
Overstock Share of Stock % = DIVIDE([Overstock Value], [Stock Value])
```

```dax
Days of Cover =
DIVIDE(SUM(Inventory[quantity_on_hand]) * 90, SUM(Inventory[units_sold_90d]))
```

Stock divided by the daily sales of the last 90 days, summed over the selection.

```dax
Suggested Order Units = SUM(Inventory[suggested_order_qty])
```

```dax
Cost of Goods Last 12 Months =
CALCULATE(
    [Cost of Goods],
    DATESINPERIOD('Date'[date_key], [Last Sales Date], -12, MONTH)
)
```

```dax
Inventory Turnover = DIVIDE([Cost of Goods Last 12 Months], [Stock Value])
```

```dax
Days of Inventory = DIVIDE(365 * [Stock Value], [Cost of Goods Last 12 Months])
```

Turnover and days of inventory use the single stock snapshot in place of the average stock, as
in `sql/analytics/09_inventory_turnover.sql`. They respond to `Product` and `Location` slicers
but not to the date slicer.

### Card-only currency display measures

The three cards on the Inventory Decisions page use text-only display measures to show Indian-scale units (crore/lakh). Keep the underlying money measures numeric: other calculations, sort logic, and future analyses must use `Stock Value`, `Replenishment Cost Estimate`, and `Stock Gap Retail Valuation`, not these display labels.

```dax
Stock Value Display =
"₹" & FORMAT(DIVIDE([Stock Value], 10000000), "0.00") & " Cr"
```

```dax
Replenishment Cost Estimate Display =
"₹" & FORMAT(DIVIDE([Replenishment Cost Estimate], 100000), "0.00") & " L"
```

```dax
Stock Gap Retail Valuation Display =
"₹" & FORMAT(DIVIDE([Stock Gap Retail Valuation], 100000), "0.00") & " L"
```

These are presentation-only strings for cards. They are not numeric measures and must not be used for further arithmetic.

## Checking the measures

Add each measure to a card (or a table) on a scratch page with no slicers and compare it with
this table. The numbers come from the loaded dataset and the SQL views, so they only match if
you loaded that dataset.

| Measure | Expected, no filters |
|---|---|
| Revenue | 209,034,798.31 |
| Cost of Goods | 166,679,469.22 |
| Gross Profit | 42,355,329.09 |
| Gross Margin % | 20.3% |
| Orders | 7,878 |
| Units Sold | 1,111,322 |
| Average Order Value | 26,533.99 |
| Active Customers | 780 |
| Customers | 800 |
| Revenue per Customer | 267,993.33 |
| Orders per Customer | 10.1 |
| Repeat Customers | 644 |
| Repeat Customer Rate % | 82.6% |
| Top 10 Customers Revenue Share % | 20.05% |
| Revenue Last 12 Months | 124,465,330.23 |
| Revenue Prior 12 Months | 84,569,468.08 |
| Revenue Growth Last 12 Months % | 47.2% |
| Cost of Goods Last 12 Months | 99,160,289.98 |
| Stock Value | 22,493,991.10 |
| Units on Hand | 139,864 |
| Stock Positions | 449 |
| Out of Stock Items | 39 |
| Stock-out Risk Items | 39 |
| Low Stock Items | 14 |
| Items Needing Action | 92 |
| Overstocked Items | 45 |
| Overstock Value | 12,693,484.09 |
| Overstock Share of Stock % | 56.4% |
| Days of Cover | 81.2 |
| Suggested Order Units | 15,641 |
| Inventory Turnover | 4.41 |
| Days of Inventory | 82.8 |

Revenue Last 12 Months and Revenue Prior 12 Months add up to Revenue. This is a good check that
the date table is marked and complete.

Time measures, in a table with `Date[year_month]` on the rows:

| Month | Revenue | Revenue PY | Revenue YoY % | Revenue PM | Revenue MoM % | New Customers |
|---|---|---|---|---|---|---|
| 2026-09 | 10,207,375.86 | 7,358,498.59 | 38.7% | 11,205,829.64 | -8.9% | 3 |
| 2026-03 | 12,211,859.98 | 7,933,968.23 | 53.9% | 8,481,575.00 | 44.0% | 22 |

If a number differs, the usual causes are a missing relationship (the model view should show
the six relationships from the diagram), a date table that is not marked, or a slicer left on
from an earlier test.
