-- Question: how did each category do in the last 6 months compared with the month before
-- and with the same month a year earlier?
--
-- LAG(revenue) with PARTITION BY category looks back inside one category only, so the
-- first month of a category is never compared with the last month of another one.
-- LAG counts rows, so every category needs a row for every month. The CROSS JOIN pairs each
-- category with each month and the left joins fill in the revenue, 0 where nothing was sold.
-- The comparison is calculated for all months and the filter on the last 6 months is
-- applied afterwards: filtering first would remove the earlier rows that LAG needs.

WITH months AS (
    SELECT generate_series(
        date_trunc('month', MIN(order_date)),
        date_trunc('month', MAX(order_date)),
        INTERVAL '1 month'
    )::date AS month
    FROM vw_fact_sales
),
monthly AS (
    SELECT
        c.category_name,
        m.month,
        COALESCE(SUM(f.net_revenue), 0) AS revenue
    FROM (SELECT DISTINCT category_name FROM vw_dim_product) AS c
    CROSS JOIN months AS m
    LEFT JOIN vw_dim_product AS p ON p.category_name = c.category_name
    LEFT JOIN vw_fact_sales AS f
        ON f.product_id = p.product_id
        AND date_trunc('month', f.order_date)::date = m.month
    GROUP BY c.category_name, m.month
),
compared AS (
    SELECT
        *,
        LAG(revenue) OVER (PARTITION BY category_name ORDER BY month) AS previous_month,
        LAG(revenue, 12) OVER (PARTITION BY category_name ORDER BY month) AS same_month_last_year
    FROM monthly
)
SELECT
    category_name,
    month,
    revenue,
    previous_month,
    ROUND(100 * (revenue - previous_month) / NULLIF(previous_month, 0), 1) AS mom_change_pct,
    same_month_last_year,
    ROUND(100 * (revenue - same_month_last_year) / NULLIF(same_month_last_year, 0), 1) AS yoy_change_pct
FROM compared
WHERE month > (SELECT MAX(month) FROM monthly) - INTERVAL '6 months'
ORDER BY category_name, month;
