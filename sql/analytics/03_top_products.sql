-- Question: which products bring in the most revenue, and do the same products make the
-- most profit?
--
-- The fact view is joined to the product dimension for names and categories. Two RANK()
-- window functions are computed over the grouped result, so the revenue rank and the
-- profit rank sit side by side. SUM(SUM(...)) OVER () is a window over the aggregated
-- rows; it gives the grand total needed for the revenue share without a second query.

SELECT
    p.product_id,
    p.product_name,
    p.category_name,
    SUM(f.quantity) AS units_sold,
    SUM(f.net_revenue) AS revenue,
    SUM(f.gross_profit) AS profit,
    ROUND(100 * SUM(f.gross_profit) / SUM(f.net_revenue), 1) AS margin_pct,
    ROUND(100 * SUM(f.net_revenue) / SUM(SUM(f.net_revenue)) OVER (), 1) AS revenue_share_pct,
    RANK() OVER (ORDER BY SUM(f.net_revenue) DESC) AS revenue_rank,
    RANK() OVER (ORDER BY SUM(f.gross_profit) DESC) AS profit_rank
FROM vw_fact_sales AS f
JOIN vw_dim_product AS p ON p.product_id = f.product_id
GROUP BY p.product_id, p.product_name, p.category_name
ORDER BY revenue DESC
LIMIT 15;
