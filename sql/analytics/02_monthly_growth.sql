-- Question: is revenue growing, and how does each month compare with the month before
-- and with the same month last year?
--
-- A CTE first reduces the data to one revenue number per month, then LAG() looks at an
-- earlier row of that result. A self-join would need a join on "month - 1"; LAG does the
-- same thing in one line.
-- LAG counts rows, not months, so there has to be a row for every month. generate_series
-- lists the months and the left join gives a month without sales a revenue of 0. Without it,
-- the month after a gap would be compared with the month before the gap.
-- NULLIF avoids a division by zero.

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
        m.month,
        COALESCE(SUM(f.net_revenue), 0) AS revenue
    FROM months AS m
    LEFT JOIN vw_fact_sales AS f ON date_trunc('month', f.order_date)::date = m.month
    GROUP BY m.month
)
SELECT
    month,
    revenue,
    LAG(revenue) OVER (ORDER BY month) AS previous_month,
    ROUND(100 * (revenue - LAG(revenue) OVER (ORDER BY month))
          / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 1) AS mom_growth_pct,
    ROUND(100 * (revenue - LAG(revenue, 12) OVER (ORDER BY month))
          / NULLIF(LAG(revenue, 12) OVER (ORDER BY month), 0), 1) AS yoy_growth_pct
FROM monthly
ORDER BY month;
