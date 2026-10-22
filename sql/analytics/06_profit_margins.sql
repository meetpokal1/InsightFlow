-- Question: which products sell a lot but earn a thin margin?
--
-- "Sells a lot" and "thin margin" are both conditions on aggregated numbers (total revenue,
-- total profit per product), so they belong in HAVING; WHERE runs before the grouping and
-- cannot see them. The reference values are calculated once: the company-wide margin in a
-- CTE and the median product revenue in a subquery inside HAVING.
-- profit_gap is the extra profit these products would add if they earned the company margin.

WITH company AS (
    SELECT SUM(gross_profit) / SUM(net_revenue) AS margin
    FROM vw_fact_sales
)
SELECT
    p.product_id,
    p.product_name,
    p.category_name,
    SUM(f.quantity) AS units_sold,
    SUM(f.net_revenue) AS revenue,
    SUM(f.gross_profit) AS profit,
    ROUND(100 * SUM(f.gross_profit) / SUM(f.net_revenue), 1) AS margin_pct,
    ROUND(100 * c.margin, 1) AS company_margin_pct,
    ROUND(SUM(f.net_revenue) * c.margin - SUM(f.gross_profit), 0) AS profit_gap
FROM vw_fact_sales AS f
JOIN vw_dim_product AS p ON p.product_id = f.product_id
CROSS JOIN company AS c
GROUP BY p.product_id, p.product_name, p.category_name, c.margin
HAVING SUM(f.net_revenue) >= (
           SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY product_revenue)
           FROM (
               SELECT SUM(net_revenue) AS product_revenue
               FROM vw_fact_sales
               GROUP BY product_id
           ) AS per_product
       )
   AND SUM(f.gross_profit) / SUM(f.net_revenue) < c.margin
ORDER BY revenue DESC;
