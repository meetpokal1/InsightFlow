-- Calendar table for Power BI (one row per day). It is filled once and can be run again safely.

CREATE TABLE IF NOT EXISTS dim_date (
    date_key      DATE PRIMARY KEY,
    year          INTEGER NOT NULL,
    quarter       INTEGER NOT NULL,
    month_number  INTEGER NOT NULL,
    month_name    VARCHAR(10) NOT NULL,
    year_month    CHAR(7) NOT NULL,
    week_of_year  INTEGER NOT NULL,
    day_of_week   INTEGER NOT NULL,
    day_name      VARCHAR(10) NOT NULL,
    is_weekend    BOOLEAN NOT NULL
);

INSERT INTO dim_date
SELECT
    d::date,
    EXTRACT(YEAR FROM d)::int,
    EXTRACT(QUARTER FROM d)::int,
    EXTRACT(MONTH FROM d)::int,
    TO_CHAR(d, 'FMMonth'),
    TO_CHAR(d, 'YYYY-MM'),
    EXTRACT(WEEK FROM d)::int,
    EXTRACT(ISODOW FROM d)::int,
    TO_CHAR(d, 'FMDay'),
    EXTRACT(ISODOW FROM d) IN (6, 7)
FROM generate_series('2023-01-01'::date, '2028-12-31'::date, interval '1 day') AS d
ON CONFLICT (date_key) DO NOTHING;
