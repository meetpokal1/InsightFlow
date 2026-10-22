# ER diagram

![ER diagram](diagrams/er_diagram.png)

The diagram is drawn from [diagrams/er_diagram.mmd](diagrams/er_diagram.mmd). PK is a primary
key, FK a foreign key and UK a unique column. The full column list with constraints is in
[database_schema.md](database_schema.md).

## Relationships

| One | Many | Foreign key | What it means |
|---|---|---|---|
| categories | products | `products.category_id` | every product has one category |
| suppliers | products | `products.supplier_id` | every product has one supplier |
| customers | orders | `orders.customer_id` | a customer places many orders |
| locations | orders | `orders.location_id` | the store or warehouse that handled the order |
| orders | order_items | `order_items.order_id` | an order has one or more lines |
| products | order_items | `order_items.product_id` | the product on a line |
| products | inventory | `inventory.product_id` | a product is stocked at several locations |
| locations | inventory | `inventory.location_id` | a location holds many products |

Deleting an order also deletes its lines (`ON DELETE CASCADE`). Every other foreign key blocks
a delete while rows still point to the parent.

## Design notes

**Grain.** One row in `order_items` is one product on one order. Revenue and profit are
calculated at this level. Facts that belong to the whole order (date, customer, location,
status, payment method) are on `orders`.

**No order total column.** The raw `orders` file has an `order_total`, but it disagreed with
the cleaned lines in 1,312 orders (see [data_quality.md](data_quality.md) for why), and it was
missing in 177 more. The clean model leaves it out and always derives totals from the lines, so
there is only one source for revenue.

**An order has at least one line.** The diagram shows this (`||--|{`), but PostgreSQL cannot
enforce "at least one child row" without triggers. The pipeline enforces it instead: an order
without a valid line is rejected before loading.

**Inventory is a snapshot.** One row is the stock of one product at one location on
`snapshot_date`. `UNIQUE (product_id, location_id, snapshot_date)` stops two rows for the same
position. There is no stock history, so the project cannot show how stock changed over time.

**Text keys.** Keys such as `C00677`, `P0010` and `L01` come from the source files and are kept
as they are. They are stable between pipeline runs, which generated numbers would not be after
a reload.

**Two tables are not in the diagram.** `etl_quality_log` (one row per problem the cleaning step
found) and `dim_date` (a calendar table for Power BI) have no foreign keys, so they would only
add loose boxes.
