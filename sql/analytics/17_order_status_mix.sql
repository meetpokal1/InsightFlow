-- Question: how many orders are cancelled or returned, and how much revenue does that remove?
--
-- Only completed orders count as sales, so cancellations and returns are invisible in the
-- revenue views. This query looks at the orders table directly. COUNT(*) FILTER (WHERE ...)
-- counts each status in one pass, and order values come from a CTE so that an order is
-- counted once even though it has several lines. ROLLUP adds the company total.

WITH order_values AS (
    SELECT
        order_id,
        SUM(quantity * unit_price * (1 - discount_pct / 100)) AS order_value
    FROM order_items
    GROUP BY order_id
)
SELECT
    COALESCE(l.location_name, 'All locations') AS location_name,
    COUNT(*) AS orders,
    COUNT(*) FILTER (WHERE o.order_status = 'Cancelled') AS cancelled,
    COUNT(*) FILTER (WHERE o.order_status = 'Returned') AS returned,
    ROUND(100.0 * COUNT(*) FILTER (WHERE o.order_status = 'Cancelled') / COUNT(*), 1) AS cancelled_pct,
    ROUND(100.0 * COUNT(*) FILTER (WHERE o.order_status = 'Returned') / COUNT(*), 1) AS returned_pct,
    ROUND(SUM(v.order_value) FILTER (WHERE o.order_status <> 'Completed')) AS value_not_recognised
FROM orders AS o
JOIN order_values AS v ON v.order_id = o.order_id
JOIN locations AS l ON l.location_id = o.location_id
GROUP BY ROLLUP (l.location_name)
ORDER BY GROUPING(l.location_name), orders DESC;
