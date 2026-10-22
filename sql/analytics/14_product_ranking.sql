-- Question: what are the best-selling products inside each category?
--
-- RANK() with PARTITION BY category restarts the ranking for every category. The share of
-- category revenue uses SUM(...) OVER (PARTITION BY ...), which is a group total without
-- collapsing the rows. Window functions cannot be filtered in WHERE of the same query, so
-- the ranking lives in a CTE and the outer query keeps the top 3 of each category.

WITH product_sales AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category_name,
        SUM(f.quantity) AS units_sold,
        SUM(f.net_revenue) AS revenue,
        SUM(f.gross_profit) AS profit
    FROM vw_fact_sales AS f
    JOIN vw_dim_product AS p ON p.product_id = f.product_id
    GROUP BY p.product_id, p.product_name, p.category_name
),
ranked AS (
    SELECT
        *,
        RANK() OVER (PARTITION BY category_name ORDER BY revenue DESC) AS rank_in_category,
        ROUND(100 * revenue / SUM(revenue) OVER (PARTITION BY category_name), 1) AS share_of_category_pct,
        RANK() OVER (ORDER BY revenue DESC) AS overall_rank
    FROM product_sales
)
SELECT
    category_name,
    rank_in_category,
    product_id,
    product_name,
    units_sold,
    revenue,
    profit,
    share_of_category_pct,
    overall_rank
FROM ranked
WHERE rank_in_category <= 3
ORDER BY category_name, rank_in_category;
