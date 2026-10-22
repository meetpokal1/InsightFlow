-- Question: how quickly does stock turn into sales?
--
-- Inventory turnover = cost of goods sold in the last 12 months / value of stock on hand.
-- Days of inventory = 365 / turnover. The database only holds one stock snapshot, so that
-- snapshot stands in for the average inventory; with monthly snapshots the average of the
-- 12 values would be the better denominator.
-- Sales and stock live in different tables, so each is summed per category in its own CTE
-- before they are joined. Joining the raw rows first would repeat every stock row once per
-- sale and inflate the totals.

WITH cogs AS (
    SELECT p.category_id, SUM(f.cost_of_goods) AS cogs_12m
    FROM vw_fact_sales AS f
    JOIN products AS p ON p.product_id = f.product_id
    WHERE f.order_date > (SELECT MAX(order_date) FROM vw_fact_sales) - INTERVAL '12 months'
    GROUP BY p.category_id
),
stock AS (
    SELECT p.category_id, SUM(i.inventory_value) AS stock_value
    FROM vw_fact_inventory AS i
    JOIN products AS p ON p.product_id = i.product_id
    GROUP BY p.category_id
)
SELECT
    COALESCE(c.category_name, 'All categories') AS category_name,
    SUM(cogs.cogs_12m) AS cogs_12m,
    SUM(stock.stock_value) AS stock_value,
    ROUND(SUM(cogs.cogs_12m) / NULLIF(SUM(stock.stock_value), 0), 2) AS turns_per_year,
    ROUND(365 * SUM(stock.stock_value) / NULLIF(SUM(cogs.cogs_12m), 0)) AS days_of_inventory
FROM cogs
JOIN stock ON stock.category_id = cogs.category_id
JOIN categories AS c ON c.category_id = cogs.category_id
GROUP BY ROLLUP (c.category_name)
ORDER BY GROUPING(c.category_name), turns_per_year DESC;
