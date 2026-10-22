-- Question: which products are about to run out, and how much should be ordered?
--
-- The status comes from vw_fact_inventory, which compares days of cover (stock divided by
-- the daily sales rate of the last 90 days) with the supplier's lead time. A product whose
-- cover is shorter than the lead time will be out of stock before a new order arrives, even
-- if it is above its reorder level today.
-- The CASE in ORDER BY puts the most urgent rows first. The suggested order quantity is
-- calculated in the view: it covers the lead time plus 30 more days of sales.

SELECT
    p.product_id,
    p.product_name,
    p.category_name,
    l.location_name,
    i.quantity_on_hand,
    i.reorder_level,
    i.avg_daily_units,
    i.days_of_cover,
    i.lead_time_days,
    i.stock_status,
    i.suggested_order_qty,
    ROUND(i.avg_daily_units * p.selling_price) AS revenue_per_day
FROM vw_fact_inventory AS i
JOIN vw_dim_product AS p ON p.product_id = i.product_id
JOIN vw_dim_location AS l ON l.location_id = i.location_id
WHERE i.stock_status IN ('Out of stock', 'Stock-out risk', 'Low stock')
ORDER BY
    CASE i.stock_status
        WHEN 'Out of stock' THEN 1
        WHEN 'Stock-out risk' THEN 2
        ELSE 3
    END,
    revenue_per_day DESC;
