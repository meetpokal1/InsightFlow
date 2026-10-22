-- Question: where do inventory and sales disagree?
--
-- Four kinds of mismatch, each found with the technique that fits it:
--   1. sold but no stock record: NOT EXISTS (an anti-join) finds sales rows with no match
--   2. stock but no sales in 90 days: a plain filter on the inventory view
--   3. selling but out of stock, and 4. overstocked: filters on the stock status
-- UNION ALL stacks the four results into one table so they can be compared. The last
-- 90 days are measured back from the snapshot date, the same window the inventory view uses.

WITH snapshot AS (
    SELECT MAX(snapshot_date) AS day FROM inventory
),
sold AS (
    SELECT
        f.product_id,
        f.location_id,
        SUM(f.quantity) AS units_sold_90d,
        SUM(f.net_revenue) AS revenue_90d
    FROM vw_fact_sales AS f
    CROSS JOIN snapshot AS s
    WHERE f.order_date > s.day - 90
    GROUP BY f.product_id, f.location_id
)
SELECT
    'Sold, but no stock record' AS mismatch_type,
    COUNT(*) AS product_locations,
    SUM(sold.units_sold_90d) AS units,
    ROUND(SUM(sold.revenue_90d)) AS value,
    'revenue of the last 90 days' AS value_is
FROM sold
WHERE NOT EXISTS (
    SELECT 1
    FROM inventory AS i
    WHERE i.product_id = sold.product_id AND i.location_id = sold.location_id
)

UNION ALL

SELECT
    'In stock, nothing sold in 90 days',
    COUNT(*),
    SUM(quantity_on_hand),
    ROUND(SUM(inventory_value)),
    'cost value of the stock'
FROM vw_fact_inventory
WHERE units_sold_90d = 0 AND quantity_on_hand > 0

UNION ALL

SELECT
    'Selling, but out of stock',
    COUNT(*),
    SUM(units_sold_90d),
    ROUND(SUM(i.units_sold_90d * p.selling_price)),
    'sales of the last 90 days at list price'
FROM vw_fact_inventory AS i
JOIN products AS p ON p.product_id = i.product_id
WHERE i.stock_status = 'Out of stock'

UNION ALL

SELECT
    'Overstocked (more than 180 days of cover)',
    COUNT(*),
    SUM(quantity_on_hand),
    ROUND(SUM(inventory_value)),
    'cost value of the stock'
FROM vw_fact_inventory
WHERE stock_status = 'Overstocked';
