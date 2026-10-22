-- Question: what share of customers order more than once?
--
-- Repeat customer rate = customers with at least 2 completed orders / customers with at
-- least 1 completed order. The CTE counts orders per customer; COUNT(*) FILTER (WHERE ...)
-- then counts the repeat customers inside the same GROUP BY, with no second pass.

WITH customer_orders AS (
    SELECT customer_id, COUNT(DISTINCT order_id) AS orders
    FROM vw_fact_sales
    GROUP BY customer_id
)
SELECT
    COALESCE(c.customer_type, 'All customers') AS customer_type,
    COUNT(*) AS customers,
    COUNT(*) FILTER (WHERE co.orders >= 2) AS repeat_customers,
    ROUND(100.0 * COUNT(*) FILTER (WHERE co.orders >= 2) / COUNT(*), 1) AS repeat_rate_pct,
    ROUND(AVG(co.orders), 1) AS avg_orders_per_customer
FROM customer_orders AS co
JOIN vw_dim_customer AS c ON c.customer_id = co.customer_id
GROUP BY ROLLUP (c.customer_type)
ORDER BY GROUPING(c.customer_type), customers DESC;
