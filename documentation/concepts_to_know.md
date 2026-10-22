# Concepts to know

The ideas behind each part of the project, where to find them in the code, and what you should be
able to explain about them. The last two sections list the changes you are most likely to make
and questions to practise on.

A good order for reading the code:

1. `src/tables.py` (the data model) and `src/cleaning/rules.py` (the business rules)
2. `src/cleaning/products.py` (a small cleaner), then `quality.py` and `clean_all.py`
3. `src/pipeline.py`, `src/database/loader.py`
4. `sql/schema/01_tables.sql`, then `04_views.sql`
5. two or three files from `sql/analytics/`
6. `api/main.py`, `api/dependencies.py`, one file in `api/routes/`
7. `tests/conftest.py`, then `tests/test_pipeline.py` and `tests/test_database.py`

## 1. The pipeline

| Concept | What it means here | Where |
|---|---|---|
| ETL | Extract (read the files), transform (clean and check), load (PostgreSQL). The steps run in that order and each one is its own module | `src/pipeline.py` |
| Reading everything as text | If pandas guessed the types, an id such as `007` would lose its zeros, a quantity column with one gap would turn into decimals (`12.0`), a column with one `₹1,676.60` in it would be text anyway and `05/03/2025` would be read month first. Reading as text means every conversion is written in the code | `src/ingestion/loader.py` |
| Profiling | Counting missing and distinct values per column before touching anything, so you know what the data looks like | `src/ingestion/profiling.py` |
| Fix or reject | A value is fixed when the right answer is known (case, spaces, a `₹` sign, the list price for a missing price). A row is rejected when it is not (a customer id that does not exist). Rejected rows are kept in a file with the reason, never dropped silently | `src/cleaning/quality.py` (`Quarantine`) |
| Quality log | A table of what was wrong, how many rows and what was done. It is a business record. It is separate from the technical log written with the `logging` module | `QualityLog`, table `etl_quality_log` |
| Validation gate | After cleaning, primary keys, required columns, foreign keys and value rules are checked. One failure stops the run before the database is touched | `src/cleaning/validators.py` |
| Repeatable load | `TRUNCATE` and the inserts run in one transaction, so running the pipeline twice gives the same database and a failure leaves the old data in place | `src/database/loader.py` |
| Determinism | The synthetic data uses a seed, and the as-of date is a parameter instead of "today". The same input gives the same output | `--seed`, `--as-of` |

You should be able to say why the pipeline rejects some rows instead of repairing them, and why
the order of the cleaning steps matters (an order line is checked against the clean orders).

## 2. Cleaning decisions

| Concept | What it means here | Where |
|---|---|---|
| Missing values | There are four options: drop the row, fill with a default (discount to 0), fill with something derived (list price, the cost ratio of the category, the median reorder level), or leave it empty (email, phone). Each column uses the option whose mistake costs least | [data_quality.md](data_quality.md) |
| Exact and business duplicates | An exact duplicate is the same row twice. A business duplicate is the same customer under two ids. The second kind needs a rule (same email, or same name and phone) and the orders must be moved to the kept id | `src/cleaning/customers.py`, `remap_ids` |
| Referential integrity | Every foreign key must point to a row that exists. A row whose parent is missing is an orphan | `find_orphans` in `validators.py` |
| Outliers | A quantity above 500 or a price three times away from the list price is treated as an error. The limits are judgement, so they are constants in one file | `src/cleaning/rules.py` |
| Date parsing | Formats are listed explicitly and day comes first. A date like `31/02/2024` becomes missing, and an order without a date is rejected | `src/cleaning/parsing.py` |
| Derived data | The raw `order_total` is ignored, because it can disagree with the lines. Totals are always calculated from the lines | `src/cleaning/sales.py` |

## 3. pandas

You need to be comfortable with:

- boolean masks and `.loc` (select and change rows by a condition)
- the `.str` methods for text
- `pd.to_numeric(..., errors="coerce")` and `pd.to_datetime(..., format=..., errors="coerce")`,
  which turn bad values into missing values instead of raising an error
- `merge` (which rows survive an inner or a left join, and how a join can repeat rows),
  `groupby` with `agg` and `transform`, `drop_duplicates`
- missing values: `isna()`, `NaN` against `pd.NA`, and the nullable `Int64` type
- in pandas 3 a DataFrame made from another one behaves like a copy, so changing it does not
  change the original
- `DataFrame.to_sql`, used with `method="multi"` and `chunksize` to insert in batches

All of it is in `src/cleaning/`. The files are short and each one cleans one table.

## 4. Database design

| Concept | What it means here | Where |
|---|---|---|
| Primary and foreign keys | Every table has a key. A foreign key makes PostgreSQL refuse a row whose parent does not exist | `sql/schema/01_tables.sql` |
| Constraints | `NOT NULL`, `UNIQUE`, `CHECK` (for example `quantity > 0`, `cost_price <= selling_price`). The Python code already checks the same things. The database is the last line of defence, and a test tries to insert broken rows | `test_the_schema_refuses_data_that_breaks_a_rule` |
| Data types | Money is `NUMERIC(12,2)`, an exact decimal. `FLOAT` stores binary approximations and adds rounding errors to sums | `01_tables.sql` |
| Normalisation | Customers, products, categories and suppliers each have their own table. An order is split into a header (`orders`) and its lines (`order_items`), a one to many relationship. The order total is not stored, because stored totals can disagree with the lines | [er_diagram.md](er_diagram.md) |
| Indexes | A B-tree index makes a lookup or a join on a column faster and every write a little slower. Primary keys and unique columns have one already. The partial index only covers completed orders. At 38,000 rows PostgreSQL may not use them, and `EXPLAIN` shows what it chose | `02_indexes.sql` |
| Views | A view is a saved query, not a copy of the data. Net revenue, stock status and the customer segments are defined once in a view, so SQL, the API and Power BI cannot disagree | `04_views.sql` |
| Transactions | A group of statements that succeeds or fails as a whole. `TRUNCATE` can be rolled back in PostgreSQL | `engine.begin()` in `loader.py` |
| Calendar table | A table with one row per day. Power BI needs it for time intelligence. In SQL a left join to a list of dates shows the days or months without sales | `03_dim_date.sql` |

## 5. SQL

| Concept | What to know | Query |
|---|---|---|
| Order of evaluation | `FROM`, `WHERE`, `GROUP BY`, `HAVING`, window functions, `SELECT`, `ORDER BY`, `LIMIT`. This is why `WHERE` cannot use a sum and why a window function cannot be filtered in the same `SELECT` | 06, 10 |
| `WHERE` or `HAVING` | `WHERE` filters rows before they are grouped. `HAVING` filters groups after | 06 |
| Joins | An inner join drops rows with no match, a left join keeps them. Joining two tables that both have many rows per key repeats rows and inflates sums. Add each side up on its own first, then join | 09 |
| Aggregate or window | `GROUP BY` collapses rows. A window function (`OVER`) calculates across rows and keeps every row | 03, 04 |
| Window frames | With `ORDER BY` the default frame treats equal values as one step. `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` adds one row at a time | 04 |
| Ranking | `RANK` leaves gaps after a tie, `DENSE_RANK` does not, `ROW_NUMBER` never ties. `NTILE(4)` cuts rows into four equal groups | 03, 10, 12, 14 |
| `LAG` | Reads a value from an earlier row, here the previous month or the same month last year. It counts rows, so there must be a row for every month | 02, 15 |
| Filling gaps | `generate_series` lists every month, a left join adds the revenue and `COALESCE` turns a missing month into 0. Without it `LAG` would compare a month with the wrong neighbour | 02, 15 |
| CTE | A named step (`WITH name AS (...)`) that makes a long query read from top to bottom | 02, 04 to 10, 14 to 17 |
| Subquery | A query inside another one. A scalar subquery returns one value, for example the median | 06, 09, 10, 15 |
| `FILTER` | Counts or sums only the rows that match inside one aggregate. Several of them replace several queries | 05, 08, 17 |
| `ROLLUP` | Adds subtotal and total rows to a `GROUP BY` | 07, 08, 09, 17 |
| `CASE` | An if/else inside a query, here for the trend label, the stock status and the sort order | 05, 10, 11 |
| `NOT EXISTS` | Finds rows with no match. `NOT IN` returns nothing when the list contains a `NULL` | 16 |
| `NULL` | `NULL = NULL` is not true. `COUNT(column)` skips nulls and `COUNT(*)` does not. `NULLIF(x, 0)` avoids a division by zero | all |
| Median | `percentile_cont(0.5) WITHIN GROUP (ORDER BY ...)`. It is not distorted by a few large values like the mean | 06, 07 |
| Dates | `date_trunc('month', d)` groups by month. Interval arithmetic such as `d - INTERVAL '12 months'` defines a period | 01, 05, 09 |

## 6. Business metrics

The definitions are in [kpi_definitions.md](kpi_definitions.md). The reasoning to be able to give:

- **Margin and markup differ.** Margin is profit divided by revenue. Markup is profit divided
  by cost. This project reports margin.
- **Average order value** adds the lines up to orders first. Averaging the lines would give the
  average line.
- **One month says little.** Month on month growth swings from -21.6% to +55.9% here. Year on
  year growth removes the seasonal effect, and the last 12 months against the 12 before is
  steadier still.
- **Concentration.** The top 10 customers are 20% of revenue. A high share means the business
  depends on a few accounts.
- **RFM** scores a customer on how recently, how often and how much they bought. The segments
  are a rule on top of the scores. They describe the data, they do not predict anything.
- **Days of cover** is stock divided by the daily sales rate. Compare it with the supplier
  **lead time**: if the stock ends before a new order could arrive, the item is at risk.
- **Overstock** is stock above a number of days of sales (180 here). It ties up money.
- **Inventory turnover** is cost of goods sold divided by stock value. A single snapshot stands
  in for the average stock, and with monthly snapshots the average would be better.
- **The suggested order** covers the lead time plus 30 days of sales. It ignores orders that
  are already on the way and has no safety stock beyond those 30 days. It is a starting point
  for a buyer and not a purchasing system.

## 7. The API

| Concept | What it means here | Where |
|---|---|---|
| REST | A resource per URL, read with `GET`, filters in the query string, JSON in the response | `api/routes/` |
| Status codes | 200 success, 404 an id that does not exist, 422 a parameter that is not valid, 503 the database is down, 500 a query failed | `api/main.py`, `dependencies.py` |
| Pydantic models | They describe each response. FastAPI checks the data against them, removes anything else and writes the Swagger documentation from them | `api/schemas/` |
| Parameter validation | `Query(50, ge=1, le=500)` and an `Enum` for allowed values make FastAPI reject a bad request with a 422 before any SQL runs | `api/routes/` |
| Dependency injection | `Depends(get_connection)` gives a route a database connection and closes it when the request ends (the function uses `yield`). The routes never create connections themselves | `api/dependencies.py` |
| App factory | `create_app(engine)` builds the app with the engine it is given, so the tests use the test database without changing any code | `api/main.py` |
| SQL injection | Values from the request reach PostgreSQL as bound parameters (`:name`), never inside the SQL text. A column name cannot be a parameter, so the sort column comes from a fixed dictionary | `src/analytics/queries.py` |
| Settings from the environment | Passwords and hosts come from environment variables or `.env`, never from the code, and `.env` is not committed | `src/config.py` |
| Middleware and handlers | Middleware logs every request with its time. Exception handlers turn database errors into clean JSON responses | `api/main.py` |

Routes are written as normal functions (`def`), not `async def`, because the database driver is
blocking. FastAPI runs them in a thread pool, so one slow query does not block the others.

## 8. Power BI

| Concept | What to know |
|---|---|
| Star schema | Facts (sales lines, stock rows) in the middle and dimensions (date, product, customer, location) around them. Filters flow from a dimension to its facts |
| Relationships | One to many, single direction. The "one" side is the dimension. Many to many and two-way filters are avoided because they make results hard to predict |
| Filter context | Every number in a visual is calculated with the filters that apply to that cell: the row, the column and the slicers. A measure is evaluated again in each context |
| Measure or column | A measure is calculated when a visual is drawn, from the filters. A calculated column is calculated once per row when the data is loaded. Totals and ratios are measures |
| `CALCULATE` | Evaluates an expression with a changed filter context. Most of the measures use it, with `REMOVEFILTERS`, `ALLSELECTED` or a date function |
| `DIVIDE` | Safe division that returns blank instead of an error |
| Time intelligence | `SAMEPERIODLASTYEAR`, `DATEADD`, `TOTALYTD` only work on a marked date table with no gaps |
| Power Query and DAX | Power Query (M) loads and shapes the tables. DAX calculates the measures. Anything that does not depend on the report filters is better done in SQL, which is why the views hold the margin and the stock status |
| Import mode | The data is copied into the report and refreshed on demand. The queries in [power_query.md](../powerbi/power_query.md) assume it |

## 9. Tests

| Concept | What it means here |
|---|---|
| Fixtures | `conftest.py` builds a small messy dataset once per run (`scope="session"`) and the tests share it |
| Markers | Tests that need PostgreSQL carry the `db` marker. They use a separate database (`DB_NAME` plus `_test`, or `TEST_DB_NAME`) and are skipped when it cannot be reached, so the real data is never touched |
| Parametrised tests | One test body runs for a list of cases, for example every broken row the schema must refuse |
| Independent calculation | The SQL views, the analytics queries and the API are compared with the same numbers worked out in pandas. If one piece of code produced both sides, the test could never fail |
| Ground truth | The generator writes what it damaged and the true totals (`_generation_manifest.json`). A test requires the pipeline to find at least 90% of each injected problem, and never more than were injected |
| Invariants | Properties that must always hold: monthly revenue adds up to the total, category shares add up to 100%, every raw row is loaded, merged, dropped or rejected |
| Determinism | Cleaning the same files twice gives identical tables |

A test is only worth having if it can fail. When a test is written, change the code it checks
on purpose and make sure the test goes red.

## 10. Project habits

- `.env` holds the secrets and is in `.gitignore`. `.env.example` shows the names without values.
- `requirements.txt` gives version ranges. The versions the project was tested with are in the
  README.
- `ruff` checks the code and `ruff format` formats it (line length 100). Run both before a commit.
- A commit does one thing and its message says what it does.
- Generated files (`data/processed`, `powerbi/data`) are not committed. The scripts recreate them.

## Changing things

| To do this | Change |
|---|---|
| Change a limit such as the quantity cap | `src/cleaning/rules.py`, run the pipeline, run the tests and update the numbers in [data_quality.md](data_quality.md) |
| Add a cleaning rule | Add it to the cleaner of that table in `src/cleaning/`. Report it with `log.add(...)` or `Quarantine.reject(...)`. Add a test to `tests/test_clean_<table>.py` |
| Add a column to a table | `src/tables.py`, `sql/schema/01_tables.sql`, the cleaner, the validator if there is a rule, the generator. Run the pipeline with `--reset-schema` |
| Change a stock rule (the 180 days, the 90 day window) | The `vw_fact_inventory` view in `sql/schema/04_views.sql`. It is the only place. Then update `test_stock_status_follows_the_documented_rules` and the docs |
| Add an analytics query | Add `sql/analytics/18_name.sql`. `scripts/run_analytics.py` and the SQL tests pick it up by itself. Add a check in `tests/test_analytics_sql.py` |
| Add an API endpoint | A function in `src/analytics/queries.py`, a response model in `api/schemas/`, a route in `api/routes/` (included in `api/main.py`), a test in `tests/test_api.py` |
| Add a Power BI measure | Put the base column in a view if it is a row level value, refresh the report, then write the measure |
| Use your own files | Put one CSV or Excel file per table in `data/raw`, named like the tables. The columns are the ones in [database_schema.md](database_schema.md), and `orders` also needs `order_total`. Rename the headers in your files to match. A missing column stops the run with a message that names it |

## Questions to practise

1. Why are the raw files read as text?
2. A customer was registered twice with different ids and has orders under both. What does the
   pipeline do, and why is the order of the steps important?
3. When does the pipeline fix a value and when does it reject the row?
4. Why is the order total ignored and calculated again from the lines?
5. Why is `NUMERIC` used for money and not `FLOAT`?
6. What is the difference between `WHERE` and `HAVING`? Show it with query 06.
7. Query 09 totals sales and stock in separate CTEs. What would go wrong with one join?
8. What does `RANK() OVER (PARTITION BY category ORDER BY revenue DESC)` do?
9. Why does `LAG(revenue, 12)` give the year on year change, and what does query 02 do for a
   month that has no sales?
10. How does the API avoid SQL injection when the caller chooses the sort column?
11. What does `Depends(get_connection)` do, and how do the tests point the API at the test
    database?
12. What is the difference between a measure and a calculated column? Why is `Gross Margin %` a
    measure?
13. Why does the Inventory table have no relationship with the Date table?
14. The tests compare SQL results with pandas. Why is that better than comparing the SQL with
    a stored expected result?
15. About 3.3% of the revenue is lost in cleaning. Where does it go, and how would a real
    business decide whether that is acceptable?
