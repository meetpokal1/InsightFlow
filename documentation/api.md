# API

A small read-only FastAPI service on top of the PostgreSQL views. It returns the numbers a
dashboard or another program would ask for, so they do not have to run SQL.

## Run it

Load the database first (`python scripts/run_pipeline.py`), then:

```bash
uvicorn api.main:app --reload
```

| URL | What |
|---|---|
| http://localhost:8000/docs | Swagger UI, where every endpoint can be tried |
| http://localhost:8000/redoc | the same documentation in ReDoc |
| http://localhost:8000/openapi.json | the OpenAPI document |

The database connection comes from the `DB_*` values in `.env` (or `DATABASE_URL`).

## Rules that apply to every endpoint

- Sales figures count **completed orders only**. Cancelled and returned orders are excluded.
- Money is in rupees, rounded to two decimals. Percentages are rounded to one decimal, except
  `revenue_share_pct`, which has two.
- Dates are `YYYY-MM-DD`. `start_date` and `end_date` are both included in the range.
- A filter value that does not exist (a location or category id) gives `404`, not an empty list.
- A period with no sales gives zeros and empty values, not an error.

## Endpoints

| Method and path | Returns |
|---|---|
| `GET /health` | `{"status": "ok"}` when the API can reach the database |
| `GET /sales/summary` | revenue, profit, margin, orders, customers, average order value, units, stock value |
| `GET /sales/monthly` | one row per month with growth against the previous month |
| `GET /products/top` | best selling products by revenue, profit or units |
| `GET /inventory/low-stock` | stock that is out, will run out before a delivery could arrive, or is at the reorder level |
| `GET /customers/top` | highest spending customers with their share of revenue |
| `GET /analytics/category-performance` | revenue, margin and 12 month trend for each category |

### GET /sales/summary

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| start_date | date | none | first order date |
| end_date | date | none | last order date |
| location_id | text | all | only this location, for example `L01` |

`inventory_value` is the cost value of the stock at the latest snapshot. Stock is a single
snapshot, so it does not change with the dates. It does change with `location_id`.

```bash
curl "http://localhost:8000/sales/summary"
```

```json
{
  "total_revenue": 209034798.31,
  "total_profit": 42355329.09,
  "margin_pct": 20.3,
  "total_orders": 7878,
  "total_customers": 780,
  "avg_order_value": 26533.99,
  "units_sold": 1111322,
  "inventory_value": 22493991.1
}
```

With filters:

```bash
curl "http://localhost:8000/sales/summary?start_date=2026-01-01&end_date=2026-03-31&location_id=L01"
```

```json
{
  "total_revenue": 5890668.02,
  "total_profit": 1134251.22,
  "margin_pct": 19.3,
  "total_orders": 219,
  "total_customers": 103,
  "avg_order_value": 26898.03,
  "units_sold": 32287,
  "inventory_value": 7016946.83
}
```

### GET /sales/monthly

Same parameters as `/sales/summary`. `mom_growth_pct` compares a month with the previous month
**in the result**, so it is empty for the first row, also when a date filter starts in the
middle of the data. A month without sales is not listed, and the month after it is compared
with the last month that is listed. (SQL query 02 lists such a month with zero revenue.)

```bash
curl "http://localhost:8000/sales/monthly"
```

The first three of the 24 rows:

```json
[
  {
    "month": "2024-10-01",
    "orders": 296,
    "revenue": 7805107.03,
    "profit": 1539219.65,
    "margin_pct": 19.7,
    "avg_order_value": 26368.6,
    "mom_growth_pct": null
  },
  {
    "month": "2024-11-01",
    "orders": 274,
    "revenue": 6690480.74,
    "profit": 1241548.73,
    "margin_pct": 18.6,
    "avg_order_value": 24417.81,
    "mom_growth_pct": -14.3
  },
  {
    "month": "2024-12-01",
    "orders": 272,
    "revenue": 7219070.42,
    "profit": 1503812.98,
    "margin_pct": 20.8,
    "avg_order_value": 26540.7,
    "mom_growth_pct": 7.9
  }
]
```

### GET /products/top

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| metric | `revenue`, `profit` or `units` | `revenue` | what to rank by |
| limit | integer 1 to 100 | 10 | how many products |
| category_id | text | all | only this category, for example `CAT01` |
| start_date, end_date | date | none | order date range |

Ties are broken by `product_id`, so the order is the same on every call.

```bash
curl "http://localhost:8000/products/top?metric=profit&limit=3"
```

```json
[
  {
    "rank": 1,
    "product_id": "P0055",
    "product_name": "Wireless Mouse",
    "category_name": "Electronics Accessories",
    "units_sold": 15725,
    "revenue": 11520836.93,
    "profit": 2977129.93,
    "margin_pct": 25.8
  },
  {
    "rank": 2,
    "product_id": "P0057",
    "product_name": "Power Bank 10000mAh",
    "category_name": "Electronics Accessories",
    "units_sold": 10197,
    "revenue": 12147650.46,
    "profit": 2875518.36,
    "margin_pct": 23.7
  },
  {
    "rank": 3,
    "product_id": "P0054",
    "product_name": "USB-C Charging Cable 1m",
    "category_name": "Electronics Accessories",
    "units_sold": 22110,
    "revenue": 7082302.37,
    "profit": 2838287.87,
    "margin_pct": 40.1
  }
]
```

### GET /inventory/low-stock

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| status | `Out of stock`, `Stock-out risk`, `Low stock` (can be repeated) | all three | which statuses to include |
| location_id | text | all | only this location |
| limit | integer 1 to 500 | 50 | how many rows |

The list starts with out of stock, then stock-out risk, then low stock. Inside each group the
items that sell the most (units per day times selling price) come first. The status rules are in
[database_schema.md](database_schema.md#vw_fact_inventory).

`suggested_order_qty` is the units needed to cover the supplier lead time plus 30 more days at
the recent sales rate, minus what is on hand, and never below 0. It is a starting point for a
buyer, not an instruction.

```bash
curl -G "http://localhost:8000/inventory/low-stock" \
  --data-urlencode "status=Out of stock" --data-urlencode "location_id=L03" \
  --data-urlencode "limit=2"
```

```json
[
  {
    "product_id": "P0037",
    "product_name": "Herbal Shampoo 340ml",
    "category_name": "Personal Care",
    "location_id": "L03",
    "location_name": "Bengaluru Warehouse",
    "quantity_on_hand": 0,
    "reorder_level": 203,
    "avg_daily_units": 8.11,
    "days_of_cover": 0.0,
    "lead_time_days": 18,
    "stock_status": "Out of stock",
    "suggested_order_qty": 390.0
  },
  {
    "product_id": "P0044",
    "product_name": "Sunscreen SPF50 100ml",
    "category_name": "Personal Care",
    "location_id": "L03",
    "location_name": "Bengaluru Warehouse",
    "quantity_on_hand": 0,
    "reorder_level": 93,
    "avg_daily_units": 4.42,
    "days_of_cover": 0.0,
    "lead_time_days": 14,
    "stock_status": "Out of stock",
    "suggested_order_qty": 195.0
  }
]
```

### GET /customers/top

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| limit | integer 1 to 100 | 10 | how many customers |
| start_date, end_date | date | none | order date range |

`revenue_share_pct` is the customer's share of all revenue in the period, not of the returned
rows.

```bash
curl "http://localhost:8000/customers/top?limit=3"
```

```json
[
  {
    "rank": 1,
    "customer_id": "C00677",
    "customer_name": "Bhatt Stores",
    "customer_type": "Wholesale",
    "city": "Bengaluru",
    "orders": 136,
    "revenue": 5797661.43,
    "revenue_share_pct": 2.77
  },
  {
    "rank": 2,
    "customer_id": "C00181",
    "customer_name": "Joshi Traders",
    "customer_type": "Wholesale",
    "city": "Kolkata",
    "orders": 123,
    "revenue": 5449096.71,
    "revenue_share_pct": 2.61
  },
  {
    "rank": 3,
    "customer_id": "C00398",
    "customer_name": "Mehta Agencies",
    "customer_type": "Wholesale",
    "city": "Chennai",
    "orders": 122,
    "revenue": 5433190.62,
    "revenue_share_pct": 2.6
  }
]
```

### GET /analytics/category-performance

No parameters. It compares the last 12 months of the data with the 12 months before. This is
the same query as `sql/analytics/05_category_performance.sql`, so the API and the SQL file
cannot disagree. The first two of the eight rows:

```json
[
  {
    "category_name": "Electronics Accessories",
    "revenue": 47853236.41,
    "profit": 13151346.33,
    "margin_pct": 27.5,
    "revenue_last_12m": 29733169.38,
    "revenue_prior_12m": 18120067.03,
    "growth_pct": 64.1,
    "share_pct": 23.9,
    "share_change_pts": 2.5,
    "trend": "Gaining share"
  },
  {
    "category_name": "Personal Care",
    "revenue": 31936981.9,
    "profit": 10116739.3,
    "margin_pct": 31.7,
    "revenue_last_12m": 18838327.25,
    "revenue_prior_12m": 13098654.65,
    "growth_pct": 43.8,
    "share_pct": 15.1,
    "share_change_pts": -0.4,
    "trend": "Steady"
  }
]
```

`trend` is `Declining` when revenue of the last 12 months is below the 12 months before. If it
is not, the label depends on the category's share of total revenue: `Gaining share` when the
share went up by more than 1 percentage point, `Losing share` when it went down by more than 1,
and `Steady` otherwise. Share is used because the whole business is growing, so almost every
category grows in absolute terms. `share_change_pts` is that change in percentage points.

## Errors

Every error has a `detail` field.

| Status | When | Example body |
|---|---|---|
| 404 | `location_id` or `category_id` does not exist, or the path is wrong | `{"detail": "Unknown location_id: L99"}` |
| 422 | a parameter has the wrong type or is out of range, or `start_date` is after `end_date` | `{"detail": "start_date must not be after end_date"}` |
| 500 | the database rejected the query | `{"detail": "The database query failed"}` |
| 503 | the database cannot be reached | `{"detail": "The database is not available"}` |

A 422 from a wrong type or range is FastAPI's standard validation body, a list of what is wrong
and where:

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["query", "limit"],
      "msg": "Input should be greater than or equal to 1",
      "input": "0",
      "ctx": {"ge": 1}
    }
  ]
}
```

Details of the exception are written to the log. They are not returned to the caller.

## Implementation notes

- `api/main.py` builds the app with `create_app(engine=None)`. Tests pass their own engine.
- Each request opens one database connection (`get_connection`) and closes it afterwards.
- The SQL is in `src/analytics/queries.py`. Request values are bound parameters. The sort
  column of `/products/top` is looked up in a fixed dictionary, never taken from the request.
- A middleware logs the method, path, status code and time of every request.
- `tests/test_api.py` compares each endpoint with an independent pandas calculation, checks
  the error cases (including a SQL injection attempt in `location_id`, which gives a plain 404)
  and checks that a missing database gives a 503.
