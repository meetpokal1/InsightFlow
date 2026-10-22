# Data quality

The raw files in `data/raw` are synthetic and deliberately messy. `scripts/generate_synthetic_data.py`
creates a clean data set first and then damages it in the ways real exports tend to be damaged.
It writes a manifest (`data/raw/_generation_manifest.json`) with the number of problems it
injected and the true totals of the clean data. That makes it possible to check how much of
the damage the pipeline finds and how much of the business it recovers, which is not possible
with real data.

All numbers on this page come from the committed raw files (seed 42, 800 customers) and the
pipeline run on them with `--as-of 2026-09-30`, the last day of the data.

## Kinds of problems in the raw files

15,052 problems were injected. The most frequent kinds:

| Kind | Examples |
|---|---|
| Duplicates | exact duplicate rows in 6 tables; 40 customers registered a second time under a new id; a location id used twice with different names; a stale second stock row for the same product and location |
| Inconsistent text | `PRIYA PATEL`, `bangalore`, `WHOLESALER`, `completed `, case and spaces in ids |
| Mixed date formats | `2024-10-01`, `01-Oct-2024`, `05/03/2025` (day first) in the same column (2,662 order dates) |
| Numbers stored as text | `₹1,676.60`, `12.0` as a quantity, `10%` as a discount (1,956 prices, 1,174 quantities, 1,174 discounts) |
| Missing values | missing email, phone, city, customer type, payment method, quantity, unit price, discount, cost price, reorder level, order total |
| Invalid values | impossible dates such as `31/02/2024`, order dates in the future, negative or zero quantity, discount above 100 |
| Outliers | quantities far above normal, prices several times the list price |
| Broken relationships | orders for an unknown or missing customer or location, lines for an unknown product, lines whose order does not exist |
| Contradictions | cost price above selling price, `order_total` that does not match the lines |

## Rows in and out

| Table | Raw rows | Exact duplicates dropped | Merged as duplicates | Rejected | Rows loaded |
|---|---|---|---|---|---|
| customers | 848 | 8 | 40 | 0 | 800 |
| products | 63 | 3 | 0 | 0 | 60 |
| categories | 8 | 1 | 0 | 0 | 8 (7 plus Uncategorized) |
| suppliers | 13 | 1 | 0 | 0 | 12 |
| locations | 9 | 1 (same location after tidying the names) | 0 | 0 | 8 |
| orders | 9,053 | 107 | 0 | 212 | 8,734 |
| order_items | 39,518 | 391 | 0 | 1,383 | 37,744 |
| inventory | 463 | 0 | 0 | 14 | 449 |

Every raw row is accounted for: loaded, dropped as a duplicate, merged or rejected. A test
checks that the sums add up for each table. Rejected rows are written to
`data/processed/rejected/` with their original row number and the reason.

| Rejected rows | Reason | Count |
|---|---|---|
| orders | order date is not a real date | 54 |
| | customer id not found | 45 |
| | customer id missing | 35 |
| | location id not found | 27 |
| | order date after the as-of date | 18 |
| | location id missing | 17 |
| | no valid line left after cleaning | 16 |
| order_items | order does not exist (or was rejected) | 964 |
| | product id not found | 152 |
| | quantity missing | 114 |
| | quantity zero | 78 |
| | quantity above 500 | 75 |
| inventory | stale second stock row for the same product and location | 9 |
| | product id not found | 5 |

## What the pipeline does with each problem

This is the content of `data_quality_report.csv` and of the `etl_quality_log` table. The
problem names in those two are written with underscores (for example `exact_duplicate_rows`)
and are reworded here in plain words.

| Table | Problem | Rows | Action |
|---|---|---|---|
| categories | exact duplicate rows | 1 | dropped |
| suppliers | exact duplicate rows | 1 | dropped |
| locations | duplicates after tidying the names | 1 | dropped |
| products | exact duplicate rows | 3 | dropped |
| products | category inferred from the supplier | 4 | used the supplier's category |
| products | missing or unknown category | 3 | set to Uncategorized |
| products | cost price above selling price | 3 | swapped the two prices |
| products | missing cost price | 2 | estimated from the category's cost ratio |
| customers | exact duplicate rows | 8 | dropped |
| customers | invalid signup date | 13 | set to missing |
| customers | signup date in the future | 2 | set to missing |
| customers | missing or unknown customer type | 25 | set to Retail |
| customers | same customer registered twice | 40 | merged into the earliest record |
| orders | exact duplicate rows | 107 | dropped |
| orders | customer id of a merged duplicate customer | 215 | moved to the kept customer |
| orders | invalid or out of range date, missing or unknown customer or location | 196 | rejected (see the table above) |
| orders | missing or unknown payment method | 177 | set to Unknown |
| orders | no valid line left | 16 | rejected |
| orders | `order_total` differs from the lines | 1,312 | kept the lines, ignored the total |
| orders | `order_total` missing | 177 | none needed, the total is derived |
| order_items | exact duplicate rows | 391 | dropped |
| order_items | order not found, unknown product, missing, zero or outlier quantity | 1,383 | rejected |
| order_items | negative quantity | 230 | sign flipped (a typing error) |
| order_items | missing unit price | 380 | set to the list price |
| order_items | unit price at least 3 times away from the list price | 117 | set to the list price |
| order_items | missing discount | 767 | set to 0 |
| order_items | discount outside 0 to 100 | 78 | set to 0 |
| inventory | invalid last restocked date | 5 | set to missing |
| inventory | negative quantity on hand | 7 | set to 0 |
| inventory | missing reorder level | 18 | filled with the median of the category |
| inventory | unknown product, stale second row | 14 | rejected |

Everything that is only about formatting (case, spaces, date formats, `₹` and `%` signs,
numbers stored as text) is fixed without a log entry, because it changes how a value is
written and not what it says.

## How much of the damage was found

For 31 kinds of injected problem the pipeline has a matching log entry. The tests require it to
find between 90% and 100% of each, and never more than were injected.

| Table | Problem | Injected | Found |
|---|---|---|---|
| customers | exact duplicate rows | 8 | 8 |
| customers | customers registered twice | 40 | 40 |
| customers | invalid signup date | 17 | 13 |
| customers | missing customer type | 25 | 25 |
| orders | exact duplicate rows | 107 | 107 |
| orders | invalid order date | 54 | 54 |
| orders | order date in the future | 18 | 18 |
| orders | unknown customer id | 45 | 45 |
| orders | missing customer id | 36 | 35 |
| orders | unknown location id | 27 | 27 |
| orders | missing location id | 18 | 17 |
| orders | missing payment method | 179 | 177 |
| orders | booked under the id of a duplicate customer | 220 | 215 |
| order_items | exact duplicate rows | 391 | 391 |
| order_items | unknown product id | 157 | 152 |
| order_items | negative quantity | 235 | 230 |
| order_items | zero quantity | 78 | 78 |
| order_items | missing quantity | 117 | 114 |
| order_items | quantity outlier | 78 | 75 |
| order_items | missing unit price | 391 | 380 |
| order_items | unit price outlier | 117 | 117 |
| order_items | missing discount | 783 | 767 |
| order_items | invalid discount | 78 | 78 |
| products | exact duplicate rows | 3 | 3 |
| products | cost price above selling price | 3 | 3 |
| products | missing cost price | 2 | 2 |
| inventory | negative quantity on hand | 7 | 7 |
| inventory | missing reorder level | 18 | 18 |
| inventory | stale duplicate stock row | 9 | 9 |
| inventory | unknown product id | 5 | 5 |

In total 3,210 of the 3,266 problems in this table were found (98.3%). The difference is rows
that carry two problems. A row is counted by the first rule that catches it: a line whose order
was rejected is rejected as "order not found" before its missing price is looked at, so the
missing price is not logged. The rule is described in the comment above `LOGGED_AS` in
`tests/test_pipeline.py`. The 4 invalid signup dates that are not counted are the placeholder
`N/A`, which the cleaner treats as an ordinary missing value (as it does `null`, `-` and
similar placeholders) instead of an invalid date.

## How much of the business was recovered

| | True value (before the damage) | In the clean data | Recovered |
|---|---|---|---|
| Customers | 800 | 800 | 100% |
| Completed orders | 8,072 | 7,878 | 97.6% |
| Order lines | 39,127 | 37,744 | 96.5% |
| Net revenue of completed orders | ₹216,134,944 | ₹209,034,798 | 96.7% |

About 3.3% of revenue is lost, because rows that cannot be repaired are rejected instead of
guessed. The largest part is the 964 lines of orders that did not exist or were rejected, then
lines with an unknown product, a missing quantity, a zero quantity or an outlier quantity. A
real business would look at the rejected files and fix the sources.

## Judgement calls to know about

- **Missing discount is set to 0** (767 lines). If those lines really had a discount, revenue
  is slightly overstated. The alternative, rejecting the line, would lose more revenue than it
  protects.
- **Missing and outlier unit prices are set to the list price** (497 lines). The list price is
  the price the product is sold at without a discount.
- **Estimated cost prices.** Two products had no cost price. It is estimated from the median
  cost-to-price ratio of their category, and the estimate is in the log.
- **A negative quantity is read as a typing error**, not as a return, because returns exist as
  an order status. 230 lines were flipped.
- **Three products stay `Uncategorized`.** Their category was missing and the supplier sells
  more than one category, so the category cannot be derived. They carry ₹14.15M of revenue
  (6.7% of the last 12 months) and appear as their own category in the reports.
- **Cost of goods uses the current cost price.** The data has no cost history, so the profit of
  old orders is only as exact as today's cost prices.
- **The raw `order_total` is not used.** It disagrees with the cleaned lines in 1,312 orders.
  Only 268 of those were damaged on purpose. In the rest the total is correct for the original
  order, but the lines were repaired or rejected afterwards. Totals are always calculated from
  the lines.
- **The as-of date.** Orders and sign-ups dated after it are invalid. It defaults to today and
  can be set with `--as-of` or `AS_OF_DATE`, so a run can be repeated exactly. For a date
  later than 30 September 2026 only one line of the quality log changes: two customers whose
  second registration is dated in October 2026 stop counting as "in the future". Those
  registrations are merged into the earlier ones, so the clean tables are the same.

## Where to look

| What | Where |
|---|---|
| Rows that were not loaded, with the reason | `data/processed/rejected/<table>_rejected.csv` |
| Counts per problem and action | `data/processed/data_quality_report.csv`, or `SELECT * FROM etl_quality_log` |
| Missing values per column in the raw files | `data/processed/raw_data_profile.csv` |
| The business rules and thresholds | `src/cleaning/rules.py` |
| What the generator injected | `data/raw/_generation_manifest.json` |
