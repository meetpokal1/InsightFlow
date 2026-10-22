-- Tables of the sales and inventory database.
-- Every statement uses IF NOT EXISTS, so the file can be run again safely.

CREATE TABLE IF NOT EXISTS categories (
    category_id    VARCHAR(10) PRIMARY KEY,
    category_name  VARCHAR(60) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id     VARCHAR(10) PRIMARY KEY,
    supplier_name   VARCHAR(100) NOT NULL,
    city            VARCHAR(60),
    contact_email   VARCHAR(120),
    lead_time_days  INTEGER NOT NULL CHECK (lead_time_days > 0)
);

CREATE TABLE IF NOT EXISTS locations (
    location_id    VARCHAR(10) PRIMARY KEY,
    location_name  VARCHAR(80) NOT NULL UNIQUE,
    city           VARCHAR(60),
    state          VARCHAR(60),
    region         VARCHAR(20) NOT NULL
                   CHECK (region IN ('North', 'South', 'East', 'West', 'Central')),
    location_type  VARCHAR(20) NOT NULL
                   CHECK (location_type IN ('Store', 'Warehouse'))
);

CREATE TABLE IF NOT EXISTS products (
    product_id     VARCHAR(10) PRIMARY KEY,
    product_name   VARCHAR(120) NOT NULL,
    category_id    VARCHAR(10) NOT NULL REFERENCES categories (category_id),
    supplier_id    VARCHAR(10) NOT NULL REFERENCES suppliers (supplier_id),
    cost_price     NUMERIC(12, 2) NOT NULL CHECK (cost_price >= 0),
    selling_price  NUMERIC(12, 2) NOT NULL CHECK (selling_price > 0),
    unit           VARCHAR(20),
    CHECK (cost_price <= selling_price)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id    VARCHAR(10) PRIMARY KEY,
    customer_name  VARCHAR(120) NOT NULL,
    email          VARCHAR(120),
    phone          VARCHAR(15),
    city           VARCHAR(60),
    customer_type  VARCHAR(20) NOT NULL
                   CHECK (customer_type IN ('Retail', 'Wholesale', 'Corporate')),
    signup_date    DATE
);

CREATE TABLE IF NOT EXISTS orders (
    order_id        VARCHAR(12) PRIMARY KEY,
    customer_id     VARCHAR(10) NOT NULL REFERENCES customers (customer_id),
    location_id     VARCHAR(10) NOT NULL REFERENCES locations (location_id),
    order_date      DATE NOT NULL,
    order_status    VARCHAR(20) NOT NULL
                    CHECK (order_status IN ('Completed', 'Cancelled', 'Returned')),
    payment_method  VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id  VARCHAR(12) PRIMARY KEY,
    order_id       VARCHAR(12) NOT NULL REFERENCES orders (order_id) ON DELETE CASCADE,
    product_id     VARCHAR(10) NOT NULL REFERENCES products (product_id),
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    unit_price     NUMERIC(12, 2) NOT NULL CHECK (unit_price > 0),
    discount_pct   NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (discount_pct BETWEEN 0 AND 100)
);

CREATE TABLE IF NOT EXISTS inventory (
    inventory_id         VARCHAR(12) PRIMARY KEY,
    product_id           VARCHAR(10) NOT NULL REFERENCES products (product_id),
    location_id          VARCHAR(10) NOT NULL REFERENCES locations (location_id),
    quantity_on_hand     INTEGER NOT NULL CHECK (quantity_on_hand >= 0),
    reorder_level        INTEGER NOT NULL CHECK (reorder_level >= 0),
    last_restocked_date  DATE,
    snapshot_date        DATE NOT NULL,
    UNIQUE (product_id, location_id, snapshot_date)
);

-- one row per problem found by the cleaning step, appended on every pipeline run
CREATE TABLE IF NOT EXISTS etl_quality_log (
    log_id         SERIAL PRIMARY KEY,
    run_at         TIMESTAMP NOT NULL DEFAULT now(),
    table_name     VARCHAR(40) NOT NULL,
    issue          VARCHAR(80) NOT NULL,
    rows_affected  INTEGER NOT NULL,
    action         VARCHAR(80) NOT NULL
);
