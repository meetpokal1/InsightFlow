# Architecture

![Architecture](diagrams/architecture.png)

The system has three parts. A Python pipeline turns the messy Excel and CSV exports into clean
tables in PostgreSQL. SQL views in the database hold the business logic once. The SQL queries,
the API and Power BI all read those views, so they show the same numbers.

## Where things live

| Folder | What it does |
|---|---|
| `data/raw` | Input files as the business would export them (3 Excel, 5 CSV). |
| `data/processed` | Pipeline output: clean CSVs, `rejected/` rows, `data_quality_report.csv`. Not committed. |
| `src/ingestion` | Reads the raw files (every column as text) and profiles them. |
| `src/cleaning` | One cleaning function per table, the business rules, the validators and the quality log. |
| `src/database` | Engine creation, running the schema files, loading the tables. |
| `src/analytics` | Runs the SQL files and holds the queries the API uses. |
| `src/synthetic` | Generates the messy raw data (seeded, so it is repeatable). |
| `src/pipeline.py` | Runs read, clean, validate, save and load in order. |
| `sql/schema` | Tables, indexes, calendar table and views. |
| `sql/analytics` | The 17 analysis queries. |
| `api` | FastAPI app, routes and response models. |
| `powerbi` | Setup guide, DAX measures, report page design, theme. |
| `scripts` | Command line entry points. |
| `tests` | pytest tests. |

## Decisions and the reasons behind them

**Read everything as text first.** If pandas guesses the types, it can change data without
saying so: a price like `₹1,676.60` stops a column from being numeric, and a date like
`05/03/2025` can be read month-first. Reading text and converting each column explicitly means
every failed conversion can be counted and logged.

**Repair when the right value is clear, reject when it is not.** A negative quantity is a typing
error, so the sign is flipped. An order without a customer cannot be repaired, so it is
rejected and written to `data/processed/rejected/`. Every repair and every rejection is a row
in the quality report.

**Check before loading.** `assert_valid` tests keys, relationships, required columns and value
rules on the cleaned data. If anything fails, the pipeline stops before it writes files or
touches the database.

**Replace the tables in one transaction.** The loader truncates the eight data tables and inserts
the new data inside one transaction. If an insert fails, PostgreSQL rolls back and the previous
data is still there.

**Business rules live in views.** `vw_fact_sales` defines net revenue and gross profit once,
`vw_fact_inventory` defines stock status once, `vw_customer_segments` defines the RFM segments
once. SQL analytics, the API and Power BI read these, so a rule changes in one file.

**Plain SQL in the API.** Every endpoint is a read-only aggregate query, so there is no ORM.
Values from the request reach PostgreSQL as bound parameters. The only text added to a statement
is a fixed fragment written in the code, for example the column name for sorting, which is
looked up in a whitelist.

**Settings come from the environment.** Database credentials and folders are read from
environment variables or a `.env` file (see `.env.example`). Nothing secret is in the code.

**Tests compare against an independent calculation.** The SQL views, the analytics queries and
the API are checked against separate pandas calculations on the same cleaned data. The raw data
generator also writes a manifest of the problems it injected. The pipeline tests generate a
small dataset, run the cleaning step and compare what it found with that manifest.

## Not included on purpose

The project does not have a scheduler, authentication on the API, a cloud deployment or a
dashboard file. The pipeline is run by hand, the API is read-only and meant to run locally, and
the Power BI report is described in [powerbi/](../powerbi/README.md) and has to be built in
Power BI Desktop. The README lists these under future improvements.
