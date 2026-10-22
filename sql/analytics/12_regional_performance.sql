-- Question: which regions and locations perform best?
--
-- One GROUP BY at location level gives every measure. Two RANK() windows run over the
-- grouped rows: one across the whole company and one inside each region (PARTITION BY),
-- so a location can be compared with all others and with its regional peers.
-- Orders and customers use COUNT(DISTINCT ...) because the fact view has one row per line.

SELECT
    l.region,
    l.location_name,
    COUNT(DISTINCT f.order_id) AS orders,
    COUNT(DISTINCT f.customer_id) AS customers,
    SUM(f.net_revenue) AS revenue,
    SUM(f.gross_profit) AS profit,
    ROUND(100 * SUM(f.gross_profit) / SUM(f.net_revenue), 1) AS margin_pct,
    ROUND(SUM(f.net_revenue) / COUNT(DISTINCT f.order_id), 2) AS avg_order_value,
    ROUND(SUM(f.net_revenue) / COUNT(DISTINCT f.customer_id), 2) AS revenue_per_customer,
    ROUND(100 * SUM(f.net_revenue) / SUM(SUM(f.net_revenue)) OVER (), 1) AS revenue_share_pct,
    RANK() OVER (ORDER BY SUM(f.net_revenue) DESC) AS overall_rank,
    RANK() OVER (PARTITION BY l.region ORDER BY SUM(f.net_revenue) DESC) AS rank_in_region
FROM vw_fact_sales AS f
JOIN vw_dim_location AS l ON l.location_id = f.location_id
GROUP BY l.region, l.location_name
ORDER BY revenue DESC;
