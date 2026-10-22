# Power Query scripts

These are the queries that load the six tables of the model. Use the PostgreSQL route when
Power BI can reach the database. Use the CSV route when it cannot (for example, when the
database runs on another machine or the connector asks for a provider you cannot install).

Open **Home > Transform data**, then for each query use **New Source > Blank Query**, open the
**Advanced Editor**, paste the code and rename the query as shown in the heading. These
scripts could not be run in the environment where the project was built (Power BI Desktop
only runs on Windows), so check the row counts at the end of this page after loading.

## PostgreSQL route

### Parameters

**Manage parameters > New parameter**, type *Text*:

| Name | Current value |
|---|---|
| ServerName | `localhost:5432` |
| DatabaseName | `sales_intelligence` |

When Power BI asks for credentials, choose *Database* and use `DB_USER` and `DB_PASSWORD` from
your `.env` file. Power BI keeps them on your computer. They are not part of the report file.
If Power BI says a provider (Npgsql) is missing, install it or use the CSV route.

### Sales

```m
let
    Source = PostgreSQL.Database(ServerName, DatabaseName),
    Sales = Source{[Schema = "public", Item = "vw_fact_sales"]}[Data]
in
    Sales
```

### Inventory

```m
let
    Source = PostgreSQL.Database(ServerName, DatabaseName),
    Inventory = Source{[Schema = "public", Item = "vw_fact_inventory"]}[Data]
in
    Inventory
```

### Product

```m
let
    Source = PostgreSQL.Database(ServerName, DatabaseName),
    Product = Source{[Schema = "public", Item = "vw_dim_product"]}[Data]
in
    Product
```

### Customer

```m
let
    Source = PostgreSQL.Database(ServerName, DatabaseName),
    Customer = Source{[Schema = "public", Item = "vw_dim_customer"]}[Data]
in
    Customer
```

### Location

```m
let
    Source = PostgreSQL.Database(ServerName, DatabaseName),
    Location = Source{[Schema = "public", Item = "vw_dim_location"]}[Data]
in
    Location
```

### Date

The calendar table in PostgreSQL runs from 2023 to 2028. This query keeps only the whole
months between the first and the last order, so a date slicer does not offer years without
data, and so "all dates" is exactly the period of the data. It reads the dates from the
`Sales` query, so it moves with the data.

```m
let
    Source = PostgreSQL.Database(ServerName, DatabaseName),
    Calendar = Source{[Schema = "public", Item = "dim_date"]}[Data],
    FirstDay = Date.StartOfMonth(List.Min(Sales[order_date])),
    LastDay = Date.EndOfMonth(List.Max(Sales[order_date])),
    Dates = Table.SelectRows(Calendar, each [date_key] >= FirstDay and [date_key] <= LastDay)
in
    Dates
```

## CSV route

Run `python scripts/export_powerbi_data.py`. It writes six files to `powerbi/data`. Create a
text parameter `DataFolder` with the full path of that folder **including the final
backslash**, for example `C:\Users\you\sales-inventory-intelligence\powerbi\data\`.

Then add one function query, named `LoadCsv`, which reads a file and sets the column types:

```m
(file_name as text, column_types as list) as table =>
let
    Source = Csv.Document(
        File.Contents(DataFolder & file_name),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Headers, column_types, "en-US")
in
    Typed
```

Each table is then a short query that calls it.

### Sales

```m
LoadCsv(
    "vw_fact_sales.csv",
    {
        {"order_item_id", type text},
        {"order_id", type text},
        {"order_date", type date},
        {"customer_id", type text},
        {"location_id", type text},
        {"product_id", type text},
        {"quantity", Int64.Type},
        {"unit_price", type number},
        {"discount_pct", type number},
        {"net_revenue", type number},
        {"cost_of_goods", type number},
        {"gross_profit", type number}
    }
)
```

### Inventory

```m
LoadCsv(
    "vw_fact_inventory.csv",
    {
        {"inventory_id", type text},
        {"product_id", type text},
        {"location_id", type text},
        {"snapshot_date", type date},
        {"quantity_on_hand", Int64.Type},
        {"reorder_level", Int64.Type},
        {"last_restocked_date", type date},
        {"lead_time_days", Int64.Type},
        {"inventory_value", type number},
        {"units_sold_90d", Int64.Type},
        {"avg_daily_units", type number},
        {"days_of_cover", type number},
        {"stock_status", type text},
        {"suggested_order_qty", type number}
    }
)
```

### Product

```m
LoadCsv(
    "vw_dim_product.csv",
    {
        {"product_id", type text},
        {"product_name", type text},
        {"category_id", type text},
        {"category_name", type text},
        {"supplier_id", type text},
        {"supplier_name", type text},
        {"lead_time_days", Int64.Type},
        {"unit", type text},
        {"cost_price", type number},
        {"selling_price", type number},
        {"list_margin_pct", type number}
    }
)
```

### Customer

```m
LoadCsv(
    "vw_dim_customer.csv",
    {
        {"customer_id", type text},
        {"customer_name", type text},
        {"city", type text},
        {"customer_type", type text},
        {"signup_date", type date},
        {"first_order_date", type date},
        {"last_order_date", type date},
        {"segment", type text}
    }
)
```

### Location

```m
LoadCsv(
    "vw_dim_location.csv",
    {
        {"location_id", type text},
        {"location_name", type text},
        {"city", type text},
        {"state", type text},
        {"region", type text},
        {"location_type", type text}
    }
)
```

### Date

```m
let
    Calendar = LoadCsv(
        "dim_date.csv",
        {
            {"date_key", type date},
            {"year", Int64.Type},
            {"quarter", Int64.Type},
            {"month_number", Int64.Type},
            {"month_name", type text},
            {"year_month", type text},
            {"week_of_year", Int64.Type},
            {"day_of_week", Int64.Type},
            {"day_name", type text},
            {"is_weekend", type logical}
        }
    ),
    FirstDay = Date.StartOfMonth(List.Min(Sales[order_date])),
    LastDay = Date.EndOfMonth(List.Max(Sales[order_date])),
    Dates = Table.SelectRows(Calendar, each [date_key] >= FirstDay and [date_key] <= LastDay)
in
    Dates
```

The CSV files are a snapshot. Run the export again after every pipeline run, then refresh.

## Check the load

After **Close & Apply**, the row counts in the model should be:

| Table | Rows |
|---|---|
| Sales | 34,007 |
| Inventory | 449 |
| Product | 60 |
| Customer | 800 |
| Location | 8 |
| Date | 730 |

`Date` has 730 rows because the data runs from 1 October 2024 to 30 September 2026. A different
number of rows in `Sales` means the pipeline was run on other data or with another `--as-of`
date. Next come the relationships ([README.md](README.md)) and the measures
([dax_measures.md](dax_measures.md)).
