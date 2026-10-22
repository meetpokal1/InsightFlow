-- Indexes for the joins and filters the analytics queries use most.
-- Primary keys and UNIQUE constraints already have an index, so they are not repeated here.
-- (UNIQUE (product_id, location_id, snapshot_date) on inventory also covers lookups by product_id.)

CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders (order_date);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_location_id ON orders (location_id);

-- almost every sales query only looks at completed orders, so a small partial index helps
CREATE INDEX IF NOT EXISTS idx_orders_completed_date
    ON orders (order_date)
    WHERE order_status = 'Completed';

CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id);

CREATE INDEX IF NOT EXISTS idx_products_category_id ON products (category_id);
CREATE INDEX IF NOT EXISTS idx_products_supplier_id ON products (supplier_id);

CREATE INDEX IF NOT EXISTS idx_inventory_location_id ON inventory (location_id);
CREATE INDEX IF NOT EXISTS idx_customers_type ON customers (customer_type);
