-- Question: what is the average order value, and how does it differ by customer type?
--
-- An order has several lines, so the lines are first added up to one value per order in a
-- CTE; averaging the lines directly would give the average line, not the average order.
-- GROUP BY ROLLUP adds an "All customers" row on top of the per-type rows.
-- The median is shown next to the mean because a few very large wholesale orders pull
-- the mean up.

WITH order_totals AS (
    SELECT order_id, customer_id, SUM(net_revenue) AS order_value
    FROM vw_fact_sales
    GROUP BY order_id, customer_id
)
SELECT
    COALESCE(c.customer_type, 'All customers') AS customer_type,
    COUNT(*) AS orders,
    ROUND(AVG(t.order_value), 2) AS avg_order_value,
    ROUND((percentile_cont(0.5) WITHIN GROUP (ORDER BY t.order_value))::numeric, 2) AS median_order_value,
    ROUND(MAX(t.order_value), 2) AS largest_order
FROM order_totals AS t
JOIN vw_dim_customer AS c ON c.customer_id = t.customer_id
GROUP BY ROLLUP (c.customer_type)
ORDER BY GROUPING(c.customer_type), avg_order_value DESC;
