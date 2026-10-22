-- Question: which customers contribute the most revenue, and how concentrated is it?
--
-- The CTE totals revenue per customer once. The window functions then work on that small
-- result: one gives each customer's share of all revenue and the other a running total
-- in ranked order (cumulative_share_pct), which shows how few customers carry the business.
-- The frame ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW is spelled out so customers
-- with equal revenue are not added together in one step.

WITH customer_revenue AS (
    SELECT
        customer_id,
        COUNT(DISTINCT order_id) AS orders,
        SUM(net_revenue) AS revenue
    FROM vw_fact_sales
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.customer_name,
    c.customer_type,
    c.city,
    cr.orders,
    cr.revenue,
    ROUND(100 * cr.revenue / SUM(cr.revenue) OVER (), 2) AS revenue_share_pct,
    ROUND(100 * SUM(cr.revenue) OVER (
              ORDER BY cr.revenue DESC, c.customer_id
              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
          ) / SUM(cr.revenue) OVER (), 2) AS cumulative_share_pct
FROM customer_revenue AS cr
JOIN vw_dim_customer AS c ON c.customer_id = cr.customer_id
ORDER BY cr.revenue DESC, c.customer_id
LIMIT 20;
