-- Views read by Power BI, the API and the analytics queries. They keep the join logic and the
-- revenue and profit formulas in one place. Sales only count completed orders; cancelled and
-- returned orders are left out. Cost of goods uses the current cost price of the product.
--
-- The views are dropped first (the ones that depend on others go first), so the file can be
-- run again after a definition changes.

DROP VIEW IF EXISTS data_assurance_reconciliation;
DROP VIEW IF EXISTS vw_fact_inventory;
DROP VIEW IF EXISTS vw_dim_location;
DROP VIEW IF EXISTS vw_dim_customer;
DROP VIEW IF EXISTS vw_customer_segments;
DROP VIEW IF EXISTS vw_dim_product;
DROP VIEW IF EXISTS vw_fact_sales;


CREATE VIEW vw_fact_sales AS
SELECT
    oi.order_item_id,
    oi.order_id,
    o.order_date,
    o.customer_id,
    o.location_id,
    oi.product_id,
    oi.quantity,
    oi.unit_price,
    oi.discount_pct,
    ROUND(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100), 2) AS net_revenue,
    ROUND(oi.quantity * p.cost_price, 2) AS cost_of_goods,
    ROUND(oi.quantity * oi.unit_price * (1 - oi.discount_pct / 100)
          - oi.quantity * p.cost_price, 2) AS gross_profit
FROM order_items AS oi
JOIN orders AS o ON o.order_id = oi.order_id
JOIN products AS p ON p.product_id = oi.product_id
WHERE o.order_status = 'Completed';


CREATE VIEW vw_dim_product AS
SELECT
    p.product_id,
    p.product_name,
    p.category_id,
    c.category_name,
    p.supplier_id,
    s.supplier_name,
    s.lead_time_days,
    p.unit,
    p.cost_price,
    p.selling_price,
    ROUND(100 * (p.selling_price - p.cost_price) / p.selling_price, 1) AS list_margin_pct
FROM products AS p
JOIN categories AS c ON c.category_id = p.category_id
JOIN suppliers AS s ON s.supplier_id = p.supplier_id;


-- RFM segments, one row per customer with at least one completed order. Recency (days since
-- the last order) and monetary value (revenue) are scored 1-4 with NTILE(4), which cuts the
-- customers into four equal groups. Frequency uses fixed bands instead, because many
-- customers share the same order count and NTILE would split equal values at random.
-- Recency is measured from the last order date in the data, not from today, so the segments
-- do not change with the day the query is run.
CREATE VIEW vw_customer_segments AS
WITH as_of AS (
    SELECT MAX(order_date) AS last_day FROM vw_fact_sales
),
rfm AS (
    SELECT
        f.customer_id,
        MIN(f.order_date) AS first_order_date,
        MAX(f.order_date) AS last_order_date,
        a.last_day - MAX(f.order_date) AS recency_days,
        COUNT(DISTINCT f.order_id) AS orders,
        SUM(f.net_revenue) AS revenue
    FROM vw_fact_sales AS f
    CROSS JOIN as_of AS a
    GROUP BY f.customer_id, a.last_day
),
scored AS (
    SELECT
        *,
        NTILE(4) OVER (ORDER BY recency_days DESC) AS recency_score,
        CASE
            WHEN orders >= 10 THEN 4
            WHEN orders >= 5 THEN 3
            WHEN orders >= 2 THEN 2
            ELSE 1
        END AS frequency_score,
        NTILE(4) OVER (ORDER BY revenue) AS monetary_score
    FROM rfm
)
SELECT
    *,
    CASE
        WHEN recency_score >= 3 AND frequency_score >= 3 THEN 'Champions'
        WHEN recency_score <= 2 AND frequency_score >= 3 THEN 'At risk'
        WHEN recency_score >= 3 AND frequency_score = 1 THEN 'New or one-time'
        WHEN recency_score = 1 THEN 'Lost'
        ELSE 'Regular'
    END AS segment
FROM scored;


CREATE VIEW vw_dim_customer AS
SELECT
    c.customer_id,
    c.customer_name,
    c.city,
    c.customer_type,
    c.signup_date,
    s.first_order_date,
    s.last_order_date,
    COALESCE(s.segment, 'No purchases') AS segment
FROM customers AS c
LEFT JOIN vw_customer_segments AS s ON s.customer_id = c.customer_id;


CREATE VIEW vw_dim_location AS
SELECT location_id, location_name, city, state, region, location_type
FROM locations;


-- Stock position per product and location, compared with how fast it sold in the 90 days
-- before the snapshot. "Stock-out risk" means the stock will run out before a new order
-- placed today could be delivered by the supplier. suggested_order_qty is the number of units
-- that covers the lead time plus 30 more days of sales, minus what is on hand.
CREATE VIEW vw_fact_inventory AS
WITH recent_sales AS (
    SELECT product_id, location_id, SUM(quantity) AS units_sold_90d
    FROM vw_fact_sales
    WHERE order_date > (SELECT MAX(snapshot_date) FROM inventory) - 90
    GROUP BY product_id, location_id
),
stock AS (
    SELECT
        i.inventory_id,
        i.product_id,
        i.location_id,
        i.snapshot_date,
        i.quantity_on_hand,
        i.reorder_level,
        i.last_restocked_date,
        s.lead_time_days,
        p.cost_price,
        p.selling_price,
        ROUND(i.quantity_on_hand * p.cost_price, 2) AS inventory_value,
        COALESCE(r.units_sold_90d, 0) AS units_sold_90d,
        ROUND(COALESCE(r.units_sold_90d, 0) / 90.0, 2) AS avg_daily_units
    FROM inventory AS i
    JOIN products AS p ON p.product_id = i.product_id
    JOIN suppliers AS s ON s.supplier_id = p.supplier_id
    LEFT JOIN recent_sales AS r
           ON r.product_id = i.product_id AND r.location_id = i.location_id
)
SELECT
    stock.*,
    CASE WHEN units_sold_90d > 0
         THEN ROUND(quantity_on_hand * 90.0 / units_sold_90d, 1)
    END AS days_of_cover,
    CASE
        WHEN units_sold_90d = 0 THEN 'No recent sales'
        WHEN quantity_on_hand = 0 THEN 'Out of stock'
        WHEN quantity_on_hand * 90.0 / units_sold_90d < lead_time_days THEN 'Stock-out risk'
        WHEN quantity_on_hand <= reorder_level THEN 'Low stock'
        WHEN quantity_on_hand * 90.0 / units_sold_90d > 180 THEN 'Overstocked'
        ELSE 'Healthy'
    END AS stock_status,
    GREATEST(CEIL(avg_daily_units * (lead_time_days + 30)) - quantity_on_hand, 0)
        AS suggested_order_qty,
    GREATEST(reorder_level - quantity_on_hand, 0) AS replenishment_quantity_required,
    ROUND(GREATEST(reorder_level - quantity_on_hand, 0) * cost_price, 2) AS replenishment_cost_estimate,
    ROUND(GREATEST(reorder_level - quantity_on_hand, 0) * selling_price, 2) AS stock_gap_retail_valuation,
    (quantity_on_hand = 0) AS is_stockout,
    (quantity_on_hand < reorder_level) AS is_below_reorder
FROM stock;


-- Pipeline reconciliation summary between raw ingestion and clean loaded records.
-- Combines current entity row counts with ETL quality log anomaly tracking for end-to-end auditability.
CREATE VIEW data_assurance_reconciliation AS
WITH latest_run AS (
    SELECT MAX(run_at) AS max_run_at FROM etl_quality_log
),
quality_summary AS (
    SELECT
        q.table_name,
        COALESCE(SUM(CASE WHEN q.action = 'dropped' THEN q.rows_affected ELSE 0 END), 0)::BIGINT AS exact_duplicates_dropped,
        COALESCE(SUM(CASE WHEN q.action = 'rejected' THEN q.rows_affected ELSE 0 END), 0)::BIGINT AS quarantined_rejected,
        COALESCE(SUM(CASE WHEN q.action LIKE '%merged%' THEN q.rows_affected ELSE 0 END), 0)::BIGINT AS merged_deduplicated
    FROM etl_quality_log q
    CROSS JOIN latest_run lr
    WHERE lr.max_run_at IS NOT NULL AND q.run_at >= lr.max_run_at - INTERVAL '10 seconds'
    GROUP BY q.table_name
),
table_counts AS (
    SELECT 'categories' AS table_name, COUNT(*)::BIGINT AS clean_loaded, 1 AS sort_order FROM categories
    UNION ALL
    SELECT 'suppliers' AS table_name, COUNT(*)::BIGINT AS clean_loaded, 2 AS sort_order FROM suppliers
    UNION ALL
    SELECT 'locations' AS table_name, COUNT(*)::BIGINT AS clean_loaded, 3 AS sort_order FROM locations
    UNION ALL
    SELECT 'products' AS table_name, COUNT(*)::BIGINT AS clean_loaded, 4 AS sort_order FROM products
    UNION ALL
    SELECT 'customers' AS table_name, COUNT(*)::BIGINT AS clean_loaded, 5 AS sort_order FROM customers
    UNION ALL
    SELECT 'orders' AS table_name, COUNT(*)::BIGINT AS clean_loaded, 6 AS sort_order FROM orders
    UNION ALL
    SELECT 'order_items' AS table_name, COUNT(*)::BIGINT AS clean_loaded, 7 AS sort_order FROM order_items
    UNION ALL
    SELECT 'inventory' AS table_name, COUNT(*)::BIGINT AS clean_loaded, 8 AS sort_order FROM inventory
),
reconciliation AS (
    SELECT
        tc.table_name,
        (tc.clean_loaded
         + COALESCE(qs.exact_duplicates_dropped, 0)
         + COALESCE(qs.quarantined_rejected, 0)
         + COALESCE(qs.merged_deduplicated, 0))::BIGINT AS raw_ingested,
        COALESCE(qs.exact_duplicates_dropped, 0)::BIGINT AS exact_duplicates_dropped,
        COALESCE(qs.quarantined_rejected, 0)::BIGINT AS quarantined_rejected,
        COALESCE(qs.merged_deduplicated, 0)::BIGINT AS merged_deduplicated,
        tc.clean_loaded,
        tc.sort_order
    FROM table_counts tc
    LEFT JOIN quality_summary qs ON qs.table_name = tc.table_name
)
SELECT
    table_name,
    raw_ingested,
    exact_duplicates_dropped,
    quarantined_rejected,
    merged_deduplicated,
    clean_loaded,
    CASE
        WHEN (raw_ingested - exact_duplicates_dropped - quarantined_rejected - merged_deduplicated) = clean_loaded
        THEN 'BALANCED'
        ELSE 'DISCREPANCY'
    END AS reconciliation_status,
    ROUND(clean_loaded::NUMERIC / NULLIF(raw_ingested, 0), 3)::DOUBLE PRECISION AS preservation_rate
FROM reconciliation
ORDER BY sort_order;
