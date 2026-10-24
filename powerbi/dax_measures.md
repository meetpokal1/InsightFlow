# DAX Measures Catalog

This reference documents the complete DAX measure architecture for InsightFlow.

- **Committed PBIP Semantic Model:** The authoritative semantic model (model.bim, loaded via definition.pbism v1.0) defines **27 active measures** (24 canonical numeric aggregations and 3 presentation-only card display measures across Sales, Inventory, and DataQualityReconciliation). The parallel TMDL representation defines **29 measure formulas**, including two auxiliary summary measures in DataQualityReconciliation.tmdl that are absent from model.bim and unreferenced in report visuals. The model contains **zero compiled calculated columns**.
- **Catalog-Only Extension Formulas:** A catalog of **22 extension measures** (time intelligence, customer RFM cohorts, and inventory velocity) and **2 suggested calculated columns** (`Status Order`, `Segment Order`) is maintained below for ad-hoc analysis and optional report enhancement. They are not compiled into the active PBIP file.

---

## 1. Implemented PBIP Semantic Model Measures (27 in Authoritative model.bim / 29 in TMDL)

Every measure below is actively compiled and validated within `powerbi/InsightFlow.SemanticModel/model.bim` and its corresponding TMDL table definitions.

### A. Sales & Commercial Performance (`Sales` Table — 12 Measures)

#### 1. `Revenue`
Sum of line-item net sales from completed orders.
```dax
Revenue = SUM(Sales[net_revenue])
```
*Format: `"₹"#,##0` · Expected Value: ₹209,034,798.31*

#### 2. `Cost of Goods`
Sum of line-item cost of goods sold.
```dax
Cost of Goods = SUM(Sales[cost_of_goods])
```
*Format: `"₹"#,##0` · Expected Value: ₹166,679,469.22*

#### 3. `Gross Profit`
Commercial gross margin dollars earned.
```dax
Gross Profit = [Revenue] - [Cost of Goods]
```
*Format: `"₹"#,##0` · Expected Value: ₹42,355,329.09*

#### 4. `Gross Margin %`
Commercial gross profit margin ratio.
```dax
Gross Margin % = DIVIDE([Gross Profit], [Revenue])
```
*Format: `0.0%` · Expected Value: 20.3%*

#### 5. `Orders`
Distinct count of completed customer purchase orders.
```dax
Orders = DISTINCTCOUNT(Sales[order_id])
```
*Format: `#,0` · Expected Value: 7,878*

#### 6. `Average Order Value`
Average commercial net revenue generated per completed order.
```dax
Average Order Value = DIVIDE([Revenue], [Orders])
```
*Format: `"₹"#,##0` · Expected Value: ₹26,533.99*

#### 7. `Units Sold`
Total quantity of physical units sold across all completed order items.
```dax
Units Sold = SUM(Sales[quantity])
```
*Format: `#,0` · Expected Value: 1,111,322*

#### 8. `Active Customers`
Distinct count of customers who completed at least one order.
```dax
Active Customers = DISTINCTCOUNT(Sales[customer_id])
```
*Format: `#,0` · Expected Value: 780*

#### 9. `Basmati Rice Net Revenue`
Flagship product (Basmati Rice 5kg / `P0010`) net revenue filter.
```dax
Basmati Rice Net Revenue = CALCULATE([Revenue], Product[product_id] = "P0010")
```
*Format: `"₹"#,##0` · Expected Value: ₹16,532,490.00*

#### 10. `Basmati Rice Gross Profit`
Flagship product realized gross margin dollars.
```dax
Basmati Rice Gross Profit = CALCULATE([Gross Profit], Product[product_id] = "P0010")
```
*Format: `"₹"#,##0` · Expected Value: ₹354,267.60*

#### 11. `Basmati Rice Margin %`
Flagship product commercial margin ratio.
```dax
Basmati Rice Margin % = CALCULATE([Gross Margin %], Product[product_id] = "P0010")
```
*Format: `0.0%` · Expected Value: 2.15%*

#### 12. `Basmati Break Even Volume Decline %`
Break-even volume tolerance under a +3% price increase: maximum volume loss before total gross profit drops below baseline.
```dax
Basmati Break Even Volume Decline % =
1 - DIVIDE(
    CALCULATE([Gross Profit], Product[product_id] = "P0010"),
    (CALCULATE([Revenue], Product[product_id] = "P0010") * 1.03) - CALCULATE([Cost of Goods], Product[product_id] = "P0010")
)
```
*Format: `0.0%` · Expected Value: 58.3%*

---

### B. Inventory Health & Capital Replenishment (`Inventory` Table — 12 Measures)

#### 13. `Stock Value`
Total warehouse inventory valuation at unit cost.
```dax
Stock Value = SUM(Inventory[inventory_value])
```
*Format: `"₹"#,##0` · Expected Value: ₹22,493,991.10*

#### 14. `Stock Value Display` (Card Display String)
Presentation string displaying stock valuation in Crores.
```dax
Stock Value Display = "₹" & FORMAT(DIVIDE([Stock Value], 10000000), "0.00") & " Cr"
```
*Format: String (Card Only) · Expected Display: ₹2.25 Cr (representing ₹22.49M / ₹22,493,991.10)*

#### 15. `Stock Positions`
Total monitored stock positions across all store and warehouse locations.
```dax
Stock Positions = COUNTROWS(Inventory)
```
*Format: `#,0` · Expected Value: 449*

#### 16. `Days of Cover`
Average days of stock cover available based on recent daily run rate.
```dax
Days of Cover = AVERAGE(Inventory[days_of_cover])
```
*Format: `0.0` · Expected Value: 81.2*

#### 17. `Items Needing Action`
Count of positions currently Out of stock, at Stock-out risk, or in Low stock status.
```dax
Items Needing Action =
CALCULATE(
    COUNTROWS(Inventory),
    Inventory[stock_status] IN {"Out of stock", "Stock-out risk", "Low stock"}
)
```
*Format: `#,0` · Expected Value: 92 (39 risk + 39 out + 14 low)*

#### 18. `Stockout Positions`
Total inventory positions with zero units on hand (`quantity_on_hand = 0`).
```dax
Stockout Positions = CALCULATE(COUNTROWS(Inventory), Inventory[quantity_on_hand] = 0)
```
*Format: `#,0` · Expected Value: 40*

#### 19. `Positions Below Reorder`
Positions where available stock has breached the designated reorder threshold.
```dax
Positions Below Reorder = CALCULATE(COUNTROWS(Inventory), Inventory[quantity_on_hand] < Inventory[reorder_level])
```
*Format: `#,0` · Expected Value: 96*

#### 20. `Replenishment Qty Required`
Physical units required to restore depleted positions to target stock levels.
```dax
Replenishment Qty Required = SUM(Inventory[replenishment_quantity_required])
```
*Format: `#,0` · Expected Value: 16,076*

#### 21. `Replenishment Cost Estimate`
Working capital required at supplier cost to purchase needed replenishment stock.
```dax
Replenishment Cost Estimate = SUM(Inventory[replenishment_cost_estimate])
```
*Format: `"₹"#,##0` · Expected Value: ₹965,992.50*

#### 22. `Replenishment Cost Estimate Display` (Card Display String)
Presentation string displaying required replenishment capital in Lakhs.
```dax
Replenishment Cost Estimate Display = "₹" & FORMAT(DIVIDE([Replenishment Cost Estimate], 100000), "0.00") & " L"
```
*Format: String (Card Only) · Expected Display: ₹9.66 L*

#### 23. `Stock Gap Retail Valuation`
Unrealized retail sales valuation represented by current stock shortages.
```dax
Stock Gap Retail Valuation = SUM(Inventory[stock_gap_retail_valuation])
```
*Format: `"₹"#,##0` · Expected Value: ₹1,341,200.00*

#### 24. `Stock Gap Retail Valuation Display` (Card Display String)
Presentation string displaying catalog stock gap in Lakhs.
```dax
Stock Gap Retail Valuation Display = "₹" & FORMAT(DIVIDE([Stock Gap Retail Valuation], 100000), "0.00") & " L"
```
*Format: String (Card Only) · Expected Display: ₹13.41 L*

---

### C. Pipeline Assurance & Data Quality (`DataQualityReconciliation` Table — 3 Measures)

#### 25. `Total Raw Records`
Total record count ingested across all 8 raw staging datasets.
```dax
Total Raw Records = SUM(DataQualityReconciliation[raw_ingested])
```
*Format: `#,0` · Expected Value: 49,975*

#### 26. `Total Clean Records`
Total validated record count loaded into production dimensional tables.
```dax
Total Clean Records = SUM(DataQualityReconciliation[clean_loaded])
```
*Format: `#,0` · Expected Value: 47,814*

#### 27. `Overall Preservation Rate %`
End-to-end data conservation efficiency.
```dax
Overall Preservation Rate % = DIVIDE([Total Clean Records], [Total Raw Records])
```
*Format: `0.0%` · Expected Value: 95.7%*

> **Auxiliary Reconciliation Measures (TMDL):**
> - `Total Duplicate Records = SUM(DataQualityReconciliation[exact_duplicates_dropped])` (Expected: 512)
> - `Total Quarantined Records = SUM(DataQualityReconciliation[quarantined_rejected])` (Expected: 1,609)

---

## 2. Suggested Calculated Columns (Catalog-Only Reference Formulas — 2 Columns)

The committed PBIP model contains zero calculated columns to preserve optimal columnar compression. If a user desires custom chart sorting in Power BI Desktop without altering source CSVs, these two reference formulas can be added as calculated columns to sort `stock_status` and `segment` respectively:

### `Status Order` (in `Inventory` Table)
Sort column for `stock_status` ensuring stockouts appear first:
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

### `Segment Order` (in `Customer` Table)
Sort column for customer RFM segments ensuring Champions appear at top:
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

---

## 3. Extension & Ad-Hoc Analytics Catalog (Catalog-Only Reference Formulas — 22 Measures)

These additional DAX measure formulas are maintained in this catalog for ad-hoc exploration, time-intelligence extensions, and deeper cohort analysis.

### Time Intelligence Measures
Time intelligence measures require a marked `Date` table.

```dax
Days Selected = DATEDIFF(MIN('Date'[date_key]), MAX('Date'[date_key]), DAY) + 1
```

```dax
Revenue PY =
IF(
    [Days Selected] <= 366,
    CALCULATE([Revenue], SAMEPERIODLASTYEAR('Date'[date_key]))
)
```

```dax
Revenue YoY % =
DIVIDE([Revenue] - [Revenue PY], [Revenue PY])
```

```dax
Revenue PM =
IF(
    [Days Selected] <= 31,
    CALCULATE([Revenue], DATEADD('Date'[date_key], -1, MONTH))
)
```

```dax
Revenue MoM % =
DIVIDE([Revenue] - [Revenue PM], [Revenue PM])
```

```dax
Revenue YTD =
TOTALYTD([Revenue], 'Date'[date_key])
```

```dax
Last Sales Date = MAX(Sales[order_date])
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
    DATESINPERIOD('Date'[date_key], DATEADD([Last Sales Date], -12, MONTH), -12, MONTH)
)
```

```dax
Revenue Growth Last 12 Months % =
DIVIDE([Revenue Last 12 Months] - [Revenue Prior 12 Months], [Revenue Prior 12 Months])
```

```dax
Revenue Share % =
DIVIDE([Revenue], CALCULATE([Revenue], ALLSELECTED(Sales)))
```

### Advanced Product & Supplier Measures

```dax
Company Gross Margin % =
CALCULATE([Gross Margin %], ALL(Product))
```

```dax
Margin Gap (pts) =
[Gross Margin %] - [Company Gross Margin %]
```

### Customer Cohort & RFM Measures

```dax
Customers = DISTINCTCOUNT(Customer[customer_id])
```

```dax
Customer Share % =
DIVIDE([Active Customers], CALCULATE([Active Customers], ALL(Customer)))
```

```dax
Revenue per Customer =
DIVIDE([Revenue], [Active Customers])
```

```dax
Orders per Customer =
DIVIDE([Orders], [Active Customers])
```

```dax
Repeat Customers =
CALCULATE(
    DISTINCTCOUNT(Sales[customer_id]),
    FILTER(
        VALUES(Sales[customer_id]),
        CALCULATE(DISTINCTCOUNT(Sales[order_id])) > 1
    )
)
```

```dax
Repeat Customer Rate % =
DIVIDE([Repeat Customers], [Active Customers])
```

```dax
New Customers =
VAR CurrentCustomers = VALUES(Sales[customer_id])
VAR PriorCustomers =
    CALCULATETABLE(
        VALUES(Sales[customer_id]),
        FILTER(
            ALL('Date'),
            'Date'[date_key] < MIN('Date'[date_key])
        )
    )
RETURN
COUNTROWS(EXCEPT(CurrentCustomers, PriorCustomers))
```

```dax
Top 10 Customers Revenue Share % =
VAR Top10Revenue =
    CALCULATE(
        [Revenue],
        TOPN(10, ALL(Customer), [Revenue], DESC)
    )
RETURN
DIVIDE(Top10Revenue, CALCULATE([Revenue], ALL(Customer)))
```

### Advanced Inventory Velocity Measures

```dax
Units on Hand = SUM(Inventory[quantity_on_hand])
```

```dax
Overstocked Items =
CALCULATE(COUNTROWS(Inventory), Inventory[stock_status] = "Overstocked")
```

```dax
Overstock Value =
CALCULATE([Stock Value], Inventory[stock_status] = "Overstocked")
```

```dax
Overstock Share of Stock % =
DIVIDE([Overstock Value], [Stock Value])
```

```dax
Cost of Goods Last 12 Months =
CALCULATE(
    [Cost of Goods],
    DATESINPERIOD('Date'[date_key], [Last Sales Date], -12, MONTH)
)
```

```dax
Inventory Turnover =
DIVIDE([Cost of Goods Last 12 Months], [Stock Value])
```

```dax
Days of Inventory =
DIVIDE(365 * [Stock Value], [Cost of Goods Last 12 Months])
```

---

## 4. Audited Baseline Verification Table

When loading the production CSV extracts with no slicers applied, verify measure outputs against these verified PostgreSQL benchmark figures:

| Measure Name | Implementation Status | Audited Baseline (No Filters) |
|---|---|---|
| `Revenue` | Implemented (Active) | 209,034,798.31 |
| `Cost of Goods` | Implemented (Active) | 166,679,469.22 |
| `Gross Profit` | Implemented (Active) | 42,355,329.09 |
| `Gross Margin %` | Implemented (Active) | 20.3% |
| `Orders` | Implemented (Active) | 7,878 |
| `Units Sold` | Implemented (Active) | 1,111,322 |
| `Average Order Value` | Implemented (Active) | 26,533.99 |
| `Active Customers` | Implemented (Active) | 780 |
| `Basmati Rice Net Revenue` | Implemented (Active) | 16,532,490.00 |
| `Basmati Rice Gross Profit` | Implemented (Active) | 354,267.60 |
| `Basmati Rice Margin %` | Implemented (Active) | 2.15% |
| `Basmati Break Even Volume Decline %` | Implemented (Active) | 58.3% |
| `Stock Value` | Implemented (Active) | 22,493,991.10 |
| `Stock Value Display` | Implemented (Active) | ₹2.25 Cr |
| `Stock Positions` | Implemented (Active) | 449 |
| `Days of Cover` | Implemented (Active) | 81.2 |
| `Items Needing Action` | Implemented (Active) | 92 |
| `Stockout Positions` | Implemented (Active) | 40 |
| `Positions Below Reorder` | Implemented (Active) | 96 |
| `Replenishment Qty Required` | Implemented (Active) | 16,076 |
| `Replenishment Cost Estimate` | Implemented (Active) | 965,992.50 |
| `Replenishment Cost Estimate Display` | Implemented (Active) | ₹9.66 L |
| `Stock Gap Retail Valuation` | Implemented (Active) | 1,341,200.00 |
| `Stock Gap Retail Valuation Display` | Implemented (Active) | ₹13.41 L |
| `Total Raw Records` | Implemented (Active) | 49,975 |
| `Total Clean Records` | Implemented (Active) | 47,814 |
| `Overall Preservation Rate %` | Implemented (Active) | 95.7% |
| `Revenue Last 12 Months` | Extension Catalog | 124,465,330.23 |
| `Revenue Prior 12 Months` | Extension Catalog | 84,569,468.08 |
| `Revenue Growth Last 12 Months %` | Extension Catalog | 47.2% |
| `Repeat Customers` | Extension Catalog | 644 |
| `Repeat Customer Rate %` | Extension Catalog | 82.6% |
| `Top 10 Customers Revenue Share %` | Extension Catalog | 20.05% |
| `Overstock Value` | Extension Catalog | 12,693,484.09 |
| `Overstock Share of Stock %` | Extension Catalog | 56.4% |
| `Cost of Goods Last 12 Months` | Extension Catalog | 99,160,289.98 |
| `Inventory Turnover` | Extension Catalog | 4.41 |
| `Days of Inventory` | Extension Catalog | 82.8 |
