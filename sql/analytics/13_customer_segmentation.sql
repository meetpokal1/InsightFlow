-- Question: which groups of customers do we have, and how much does each group matter?
--
-- The segments come from vw_customer_segments (RFM: Recency, Frequency, Monetary value).
-- The view scores every customer in CTEs and labels the segment with a CASE expression, and
-- Power BI reads the same segment column, so the report and this query always agree.
-- This query only has to add the customers up per segment: GROUP BY for the totals and
-- window functions (SUM() OVER ()) for the share of each segment in the whole.

SELECT
    segment,
    COUNT(*) AS customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS customer_share_pct,
    SUM(revenue) AS revenue,
    ROUND(100 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 1) AS revenue_share_pct,
    ROUND(AVG(recency_days)) AS avg_days_since_last_order,
    ROUND(AVG(orders), 1) AS avg_orders
FROM vw_customer_segments
GROUP BY segment
ORDER BY revenue DESC;
