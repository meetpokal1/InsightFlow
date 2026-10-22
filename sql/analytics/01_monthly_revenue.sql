-- Question: how much do we sell each month, and how profitable is it?
--
-- GROUP BY on date_trunc('month', ...) turns one row per order line into one row per month.
-- Orders are counted with COUNT(DISTINCT order_id) because an order has several lines;
-- a plain COUNT(*) would count lines instead of orders.

SELECT
    date_trunc('month', order_date)::date AS month,
    COUNT(DISTINCT order_id) AS orders,
    COUNT(DISTINCT customer_id) AS active_customers,
    SUM(net_revenue) AS revenue,
    SUM(gross_profit) AS profit,
    ROUND(100 * SUM(gross_profit) / SUM(net_revenue), 1) AS margin_pct,
    ROUND(SUM(net_revenue) / COUNT(DISTINCT order_id), 2) AS avg_order_value
FROM vw_fact_sales
GROUP BY 1
ORDER BY 1;
