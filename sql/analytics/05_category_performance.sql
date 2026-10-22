-- Question: which categories earn the most, and which are growing or losing ground?
--
-- SUM(...) FILTER (WHERE ...) puts the last 12 months and the 12 months before them side
-- by side in a single pass over the data. The first CTE finds the last sales date, so no
-- date is hard-coded and the query keeps working when new data is loaded. A year is 12
-- calendar months back from that date.
-- Every category grows when the whole business grows, so the trend label also looks at
-- the change in revenue share (in percentage points): who grows faster than the rest.

WITH bounds AS (
    SELECT MAX(order_date) AS last_day FROM vw_fact_sales
),
category_sales AS (
    SELECT
        p.category_name,
        SUM(f.net_revenue) AS revenue,
        SUM(f.gross_profit) AS profit,
        SUM(f.net_revenue) FILTER (
            WHERE f.order_date > b.last_day - INTERVAL '12 months'
        ) AS revenue_last_12m,
        SUM(f.net_revenue) FILTER (
            WHERE f.order_date <= b.last_day - INTERVAL '12 months'
            AND f.order_date > b.last_day - INTERVAL '24 months'
        ) AS revenue_prior_12m
    FROM vw_fact_sales AS f
    JOIN vw_dim_product AS p ON p.product_id = f.product_id
    CROSS JOIN bounds AS b
    GROUP BY p.category_name
),
with_share AS (
    SELECT
        *,
        100 * revenue_last_12m / SUM(revenue_last_12m) OVER () AS share_last_12m,
        100 * revenue_prior_12m / SUM(revenue_prior_12m) OVER () AS share_prior_12m
    FROM category_sales
)
SELECT
    category_name,
    revenue,
    profit,
    ROUND(100 * profit / revenue, 1) AS margin_pct,
    revenue_last_12m,
    revenue_prior_12m,
    ROUND(100 * (revenue_last_12m - revenue_prior_12m) / NULLIF(revenue_prior_12m, 0), 1) AS growth_pct,
    ROUND(share_last_12m, 1) AS share_pct,
    ROUND(share_last_12m - share_prior_12m, 1) AS share_change_pts,
    CASE
        WHEN revenue_last_12m < revenue_prior_12m THEN 'Declining'
        WHEN share_last_12m - share_prior_12m > 1 THEN 'Gaining share'
        WHEN share_last_12m - share_prior_12m < -1 THEN 'Losing share'
        ELSE 'Steady'
    END AS trend
FROM with_share
ORDER BY revenue_last_12m DESC;
