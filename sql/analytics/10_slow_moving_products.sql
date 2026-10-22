-- Question: which products sell slowly compared with the stock we hold, and how much money
-- is tied up in them?
--
-- "Slow" is measured as days of cover: units in stock divided by the daily sales rate of the
-- last 90 days. Counting units sold instead would call every expensive product slow, however
-- much revenue it brings in. Sales (company-wide) and stock (all locations) come from
-- different tables, so each is totalled per product in its own CTE and then joined.
-- NTILE(4) splits the products into four equal groups by days of cover. Group 1 has the
-- highest cover, so it is the slowest quarter. Products with no sales have no days of cover
-- (NULL) and are sorted first on purpose. A window function cannot be used in WHERE, which
-- is why the ranking is done in a CTE and the filter is applied to its result.

WITH recent_sales AS (
    SELECT product_id, SUM(quantity) AS units_sold_90d
    FROM vw_fact_sales
    WHERE order_date > (SELECT MAX(snapshot_date) FROM inventory) - 90
    GROUP BY product_id
),
product_stock AS (
    SELECT
        product_id,
        SUM(quantity_on_hand) AS units_in_stock,
        SUM(inventory_value) AS stock_value
    FROM vw_fact_inventory
    GROUP BY product_id
),
cover AS (
    SELECT
        ps.product_id,
        ps.units_in_stock,
        ps.stock_value,
        COALESCE(rs.units_sold_90d, 0) AS units_sold_90d,
        ps.units_in_stock * 90.0 / NULLIF(rs.units_sold_90d, 0) AS days_of_cover
    FROM product_stock AS ps
    LEFT JOIN recent_sales AS rs ON rs.product_id = ps.product_id
),
ranked AS (
    SELECT
        *,
        NTILE(4) OVER (ORDER BY days_of_cover DESC NULLS FIRST) AS cover_quartile
    FROM cover
)
SELECT
    p.product_id,
    p.product_name,
    p.category_name,
    r.units_in_stock,
    r.stock_value,
    r.units_sold_90d,
    ROUND(r.days_of_cover) AS days_of_cover,
    CASE WHEN r.units_sold_90d = 0 THEN 'Dead stock' ELSE 'Slow moving' END AS classification
FROM ranked AS r
JOIN vw_dim_product AS p ON p.product_id = r.product_id
WHERE r.cover_quartile = 1
ORDER BY r.stock_value DESC;
