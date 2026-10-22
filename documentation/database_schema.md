# Database schema

Developed and tested on PostgreSQL 16. The SQL lives in `sql/schema/` and runs in file name
order:

| File | Creates |
|---|---|
| `01_tables.sql` | the eight data tables and `etl_quality_log` |
| `02_indexes.sql` | indexes for the joins and filters the queries use |
| `03_dim_date.sql` | the calendar table `dim_date` (2023-01-01 to 2028-12-31) |
| `04_views.sql` | six views used by the analytics queries, the API and Power BI |

`python scripts/run_pipeline.py` runs these files itself. To create the schema by hand:

```bash
psql -U sales_user -d sales_intelligence -f sql/schema/01_tables.sql
psql -U sales_user -d sales_intelligence -f sql/schema/02_indexes.sql
psql -U sales_user -d sales_intelligence -f sql/schema/03_dim_date.sql
psql -U sales_user -d sales_intelligence -f sql/schema/04_views.sql
```

Every file can be run again. The tables use `IF NOT EXISTS`, the calendar insert uses
`ON CONFLICT DO NOTHING`, and the views are dropped and created again.

## Tables

The relationships are drawn in [er_diagram.md](er_diagram.md). Types are the PostgreSQL types.

### categories

| Column | Type | Constraints |
|---|---|---|
| category_id | VARCHAR(10) | primary key |
| category_name | VARCHAR(60) | not null, unique |

### suppliers

| Column | Type | Constraints |
|---|---|---|
| supplier_id | VARCHAR(10) | primary key |
| supplier_name | VARCHAR(100) | not null |
| city | VARCHAR(60) | |
| contact_email | VARCHAR(120) | |
| lead_time_days | INTEGER | not null, greater than 0 |

### locations

| Column | Type | Constraints |
|---|---|---|
| location_id | VARCHAR(10) | primary key |
| location_name | VARCHAR(80) | not null, unique |
| city | VARCHAR(60) | |
| state | VARCHAR(60) | |
| region | VARCHAR(20) | not null, one of North, South, East, West, Central |
| location_type | VARCHAR(20) | not null, Store or Warehouse |

### products

| Column | Type | Constraints |
|---|---|---|
| product_id | VARCHAR(10) | primary key |
| product_name | VARCHAR(120) | not null |
| category_id | VARCHAR(10) | not null, foreign key to categories |
| supplier_id | VARCHAR(10) | not null, foreign key to suppliers |
| cost_price | NUMERIC(12,2) | not null, at least 0 |
| selling_price | NUMERIC(12,2) | not null, greater than 0 |
| unit | VARCHAR(20) | |

Table check: `cost_price <= selling_price`.

### customers

| Column | Type | Constraints |
|---|---|---|
| customer_id | VARCHAR(10) | primary key |
| customer_name | VARCHAR(120) | not null |
| email | VARCHAR(120) | |
| phone | VARCHAR(15) | |
| city | VARCHAR(60) | |
| customer_type | VARCHAR(20) | not null, Retail, Wholesale or Corporate |
| signup_date | DATE | |

### orders

| Column | Type | Constraints |
|---|---|---|
| order_id | VARCHAR(12) | primary key |
| customer_id | VARCHAR(10) | not null, foreign key to customers |
| location_id | VARCHAR(10) | not null, foreign key to locations |
| order_date | DATE | not null |
| order_status | VARCHAR(20) | not null, Completed, Cancelled or Returned |
| payment_method | VARCHAR(30) | not null |

### order_items

| Column | Type | Constraints |
|---|---|---|
| order_item_id | VARCHAR(12) | primary key |
| order_id | VARCHAR(12) | not null, foreign key to orders, `ON DELETE CASCADE` |
| product_id | VARCHAR(10) | not null, foreign key to products |
| quantity | INTEGER | not null, greater than 0 |
| unit_price | NUMERIC(12,2) | not null, greater than 0 |
| discount_pct | NUMERIC(5,2) | not null, default 0, between 0 and 100 |

### inventory

| Column | Type | Constraints |
|---|---|---|
| inventory_id | VARCHAR(12) | primary key |
| product_id | VARCHAR(10) | not null, foreign key to products |
| location_id | VARCHAR(10) | not null, foreign key to locations |
| quantity_on_hand | INTEGER | not null, at least 0 |
| reorder_level | INTEGER | not null, at least 0 |
| last_restocked_date | DATE | |
| snapshot_date | DATE | not null |

Unique: `(product_id, location_id, snapshot_date)`.

### etl_quality_log

One row per problem type and table, added by every pipeline run.

| Column | Type | Constraints |
|---|---|---|
| log_id | SERIAL | primary key |
| run_at | TIMESTAMP | not null, default `now()` |
| table_name | VARCHAR(40) | not null |
| issue | VARCHAR(80) | not null |
| rows_affected | INTEGER | not null |
| action | VARCHAR(80) | not null |

### dim_date

One row per day. It exists for Power BI, where a separate calendar table is needed for
time intelligence (month to date, same period last year and so on).

| Column | Type | Example |
|---|---|---|
| date_key | DATE, primary key | 2026-09-30 |
| year | INTEGER | 2026 |
| quarter | INTEGER | 3 |
| month_number | INTEGER | 9 |
| month_name | VARCHAR(10) | September |
| year_month | CHAR(7) | 2026-09 |
| week_of_year | INTEGER | 40 (ISO week, so 1 January can be week 52 or 53 of the previous year) |
| day_of_week | INTEGER | 3 (Monday is 1) |
| day_name | VARCHAR(10) | Wednesday |
| is_weekend | BOOLEAN | false |

## Indexes

Primary keys and unique constraints already have an index, so they are not repeated here.

| Index | On | Why |
|---|---|---|
| idx_orders_order_date | orders (order_date) | date range filters |
| idx_orders_completed_date | orders (order_date) where order_status = 'Completed' | partial index, because almost every sales query only reads completed orders |
| idx_orders_customer_id | orders (customer_id) | joins and customer queries |
| idx_orders_location_id | orders (location_id) | regional queries |
| idx_order_items_order_id | order_items (order_id) | the join from orders to lines |
| idx_order_items_product_id | order_items (product_id) | product queries |
| idx_products_category_id | products (category_id) | category queries |
| idx_products_supplier_id | products (supplier_id) | supplier lookups |
| idx_inventory_location_id | inventory (location_id) | stock per location |
| idx_customers_type | customers (customer_type) | customer type breakdowns |

At this size (about 38,000 order lines) the indexes are unlikely to make a visible difference.
They are there because these are the joins and filters the queries use, and they matter once
the tables grow. `EXPLAIN` shows whether PostgreSQL uses an index for a query.

## Views

The views keep the formulas in one place. Power BI, the API and the analytics queries read them
instead of repeating the joins.

### vw_fact_sales

One row per order line of a **completed** order. Cancelled and returned orders are not in it.

| Column | Meaning |
|---|---|
| order_item_id, order_id, order_date, customer_id, location_id, product_id | keys and the order date |
| quantity, unit_price, discount_pct | from `order_items` |
| net_revenue | `ROUND(quantity * unit_price * (1 - discount_pct / 100), 2)` |
| cost_of_goods | `ROUND(quantity * cost_price, 2)`, with the current cost price of the product |
| gross_profit | `net_revenue - cost_of_goods` |

The cost price is the current one, because the data has no cost history. If costs changed in
the past, the profit of old orders is not exact.

### vw_dim_product

Product with its category and supplier: `product_id, product_name, category_id, category_name,
supplier_id, supplier_name, lead_time_days, unit, cost_price, selling_price, list_margin_pct`.
`list_margin_pct` is `(selling_price - cost_price) / selling_price` at list price. It is not the
margin actually earned, because order lines can have discounts.

### vw_customer_segments

One row per customer with at least one completed order. It scores each customer on recency,
frequency and monetary value (RFM) and gives a segment.

| Score | How it is calculated |
|---|---|
| recency_score | days since the last order, measured from the last order date in the data, split into four equal groups with `NTILE(4)`; 4 is the most recent |
| frequency_score | fixed bands on the number of orders: 10 or more = 4, 5 to 9 = 3, 2 to 4 = 2, 1 = 1 |
| monetary_score | revenue, split into four equal groups with `NTILE(4)`; 4 is the highest |

Frequency uses fixed bands because many customers have the same number of orders, and `NTILE`
would split equal values into different groups. Recency is measured from the last date in the
data rather than from today, so the segments do not change depending on the day the query runs.

| Segment | Rule | Customers in this dataset |
|---|---|---|
| Champions | recency score 3 or 4 and frequency score 3 or 4 | 311 |
| At risk | recency score 1 or 2 and frequency score 3 or 4 | 111 |
| New or one-time | recency score 3 or 4 and frequency score 1 | 12 |
| Lost | recency score 1 and frequency score 1 or 2 | 173 |
| Regular | everyone else (recency score 2 with frequency 1 or 2, or recency 3 or 4 with frequency 2) | 173 |

The rules are checked top to bottom. The segment rules do not use the monetary score. It is in
the view so a report can rank customers by value inside a segment.

### vw_dim_customer

Customer attributes plus `first_order_date`, `last_order_date` and `segment`. Customers with no
completed order get the segment `No purchases` (20 customers in this dataset).

### vw_dim_location

`location_id, location_name, city, state, region, location_type`.

### vw_fact_inventory

One row per product and location in the stock snapshot, compared with how fast the product sold
in the 90 days before the snapshot date.

| Column | Meaning |
|---|---|
| inventory_id, product_id, location_id, snapshot_date, quantity_on_hand, reorder_level, last_restocked_date | from `inventory` |
| lead_time_days | the supplier's lead time for the product |
| inventory_value | `quantity_on_hand * cost_price` |
| units_sold_90d | units sold at this location in the 90 days up to the snapshot |
| avg_daily_units | `units_sold_90d / 90` |
| days_of_cover | `quantity_on_hand * 90 / units_sold_90d`, empty when nothing sold |
| stock_status | see below |
| suggested_order_qty | `CEIL(avg_daily_units * (lead_time_days + 30)) - quantity_on_hand`, never below 0: the units that cover the lead time plus 30 more days of sales |

`stock_status` is the first rule that matches, from the top:

| Status | Rule | Rows in this dataset |
|---|---|---|
| No recent sales | nothing sold in the last 90 days | 20 |
| Out of stock | quantity on hand is 0 | 39 |
| Stock-out risk | days of cover is below the supplier lead time, so a new order would arrive too late | 39 |
| Low stock | quantity on hand is at or below the reorder level | 14 |
| Overstocked | more than 180 days of cover | 45 |
| Healthy | none of the above | 292 |

The 90 day window, the 180 day limit and the use of the lead time are choices made for this
project. They are written in the view, so they can be changed in one place.
