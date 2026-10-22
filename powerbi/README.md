# Power BI

The dashboard is a Power BI report on top of the PostgreSQL views. A `.pbix` file is not in this
repository, because Power BI Desktop only runs on Windows and the project was built somewhere
else. This folder holds everything needed to build the report, and a way to check that it is
right.

| File | What it is |
|---|---|
| [power_query.md](power_query.md) | The queries that load the six tables (PostgreSQL, or CSV files as a fallback) |
| [dax_measures.md](dax_measures.md) | The 44 measures and 2 calculated columns, each with an expected value to check |
| [report_pages.md](report_pages.md) | The four pages, visual by visual |
| `theme.json` | Colours and fonts, imported with View > Themes > Browse for themes |
| `star_schema.mmd`, `star_schema.png` | The data model diagram (the `.mmd` is the source) |
| `screenshots/` | Wireframes of the four pages. Replace them with real screenshots |
| `../scripts/export_powerbi_data.py` | Writes the tables to `powerbi/data/*.csv` for the CSV route |

## What you need

- Power BI Desktop (Windows).
- The database loaded: `python scripts/run_pipeline.py` (see the main README).
- The database user and password from your `.env`.

## Steps

1. **Load the data.** Follow [power_query.md](power_query.md). You end up with six tables:
   `Sales`, `Inventory`, `Product`, `Customer`, `Location` and `Date`.
2. **Check the row counts** at the end of that page.
3. **Create the relationships** (Model view), as in the table below. Power BI may detect some
   of them by itself. Check every one.
4. **Prepare the model** as in the first section of [dax_measures.md](dax_measures.md): mark
   `Date` as the date table, set the sort columns, add the two calculated columns.
5. **Add the measures** from [dax_measures.md](dax_measures.md) and check them against the
   expected values.
6. **Apply the theme**, then build the four pages from [report_pages.md](report_pages.md).
7. **Export screenshots** to `screenshots/` over the wireframes with the same file names. The
   main README shows them.

After the pipeline is run again with new data, use **Home > Refresh**.

## Data model

![Star schema](star_schema.png)

A star schema has fact tables, which hold events and numbers, and dimension tables, which
describe them. A slicer on a dimension filters the facts.

| Table | Source | One row is | Role |
|---|---|---|---|
| Sales | `vw_fact_sales` | one line of a completed order | fact |
| Inventory | `vw_fact_inventory` | one product at one location in the stock snapshot | fact |
| Date | `dim_date` | one day | dimension |
| Product | `vw_dim_product` | one product, with its category and supplier | dimension |
| Customer | `vw_dim_customer` | one customer, with their RFM segment | dimension |
| Location | `vw_dim_location` | one store or warehouse | dimension |

Relationships. All are one to many, single direction (from the dimension to the fact), active.

| From (one) | To (many) |
|---|---|
| `Date[date_key]` | `Sales[order_date]` |
| `Product[product_id]` | `Sales[product_id]` |
| `Customer[customer_id]` | `Sales[customer_id]` |
| `Location[location_id]` | `Sales[location_id]` |
| `Product[product_id]` | `Inventory[product_id]` |
| `Location[location_id]` | `Inventory[location_id]` |

Why it is built like this:

- **The views do the work.** Net revenue, gross profit, stock status and the customer segments
  are calculated once in PostgreSQL ([database_schema.md](../documentation/database_schema.md)).
  The report only adds them up. SQL, the API and Power BI therefore show the same numbers.
- **`Product` and `Location` are shared by both facts.** A category or location slicer filters
  sales and stock together.
- **`Date` and `Customer` only reach `Sales`.** Stock is a single snapshot, so a date slicer
  does not change it, and the inventory page has no date slicer. A customer type slicer does
  not change stock either.
- **Only completed orders are loaded.** Cancelled and returned orders are not in the model. Their
  numbers are in `sql/analytics/17_order_status_mix.sql`. To report on them in Power BI, load the
  `orders` table too and relate it to `Date`, `Customer` and `Location`.
- **A separate calendar table.** Time intelligence (same month last year, year to date) needs a
  continuous date table, which the order lines do not provide.
- **Hide the key columns** of the fact tables in the Model view (right-click > Hide in report
  view) so nobody drags an id into a chart.

## Colours

`theme.json` sets eight series colours that Power BI uses in order. Keep the order: neighbouring
colours were checked against each other for colour-blind readers in this order. Single-series
charts use the first colour (blue). The pages as designed use no other series colour, because
the comparison line in the monthly revenue chart is grey. The green, gold and pink in the list
are too light to be read against the background without labels, so a chart that uses them
needs data labels or the table view.

Stock status has its own colours, set by hand on the charts that show it. The colour never
carries the meaning alone, because the status is always written out too (axis, legend or a
column). The icon rule in the product matrix shows the margin number next to the warning icon.

| Meaning | Colour |
|---|---|
| Good, healthy | `#0CA30C` |
| Warning, low stock | `#FAB219` |
| Serious, stock-out risk | `#EC835A` |
| Critical, out of stock | `#D03B3B` |
| Overstocked | `#2A78D6` |
| No data, no recent sales | `#898781` |

The theme file was not loaded into Power BI Desktop where it was written. If Power BI reports
an error when importing it, delete the `visualStyles` block. The colours and fonts then still
apply, and you can set backgrounds and borders by hand.
