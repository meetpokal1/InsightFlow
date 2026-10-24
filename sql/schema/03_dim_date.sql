-- Calendar table for Power BI. The schema mirrors the PBIP Date table.
-- The table is populated across the supported 2023-2028 reporting horizon.

CREATE TABLE IF NOT EXISTS dim_date (
    date_key      DATE PRIMARY KEY,
    year          INTEGER NOT NULL,
    quarter       INTEGER NOT NULL,
    quarter_name  VARCHAR(2) NOT NULL,
    month         INTEGER NOT NULL,
    month_name    VARCHAR(10) NOT NULL,
    year_month    CHAR(7) NOT NULL,
    day           INTEGER NOT NULL,
    day_of_week   INTEGER NOT NULL,
    day_name      VARCHAR(10) NOT NULL,
    is_weekend    BOOLEAN NOT NULL
);

-- Migrate the earlier SQL-only calendar schema to the PBIP field contract.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'dim_date'
          AND column_name = 'month_number'
    ) THEN
        ALTER TABLE dim_date RENAME COLUMN month_number TO month;
    END IF;

    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'dim_date'
          AND column_name = 'week_of_year'
    ) THEN
        ALTER TABLE dim_date RENAME COLUMN week_of_year TO day;
        UPDATE dim_date SET day = EXTRACT(DAY FROM date_key)::int;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'dim_date'
          AND column_name = 'quarter_name'
    ) THEN
        ALTER TABLE dim_date ADD COLUMN quarter_name VARCHAR(2);
        UPDATE dim_date SET quarter_name = 'Q' || quarter::text;
        ALTER TABLE dim_date ALTER COLUMN quarter_name SET NOT NULL;
    END IF;
END $$;

INSERT INTO dim_date (
    date_key, year, quarter, quarter_name, month, month_name, year_month,
    day, day_of_week, day_name, is_weekend
)
SELECT
    d::date,
    EXTRACT(YEAR FROM d)::int,
    EXTRACT(QUARTER FROM d)::int,
    'Q' || EXTRACT(QUARTER FROM d)::int::text,
    EXTRACT(MONTH FROM d)::int,
    TO_CHAR(d, 'FMMonth'),
    TO_CHAR(d, 'YYYY-MM'),
    EXTRACT(DAY FROM d)::int,
    EXTRACT(ISODOW FROM d)::int,
    TO_CHAR(d, 'FMDay'),
    EXTRACT(ISODOW FROM d) IN (6, 7)
FROM generate_series('2023-01-01'::date, '2028-12-31'::date, interval '1 day') AS d
ON CONFLICT (date_key) DO UPDATE SET
    year = EXCLUDED.year,
    quarter = EXCLUDED.quarter,
    quarter_name = EXCLUDED.quarter_name,
    month = EXCLUDED.month,
    month_name = EXCLUDED.month_name,
    year_month = EXCLUDED.year_month,
    day = EXCLUDED.day,
    day_of_week = EXCLUDED.day_of_week,
    day_name = EXCLUDED.day_name,
    is_weekend = EXCLUDED.is_weekend;
