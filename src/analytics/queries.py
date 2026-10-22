"""SQL used by the API.

The queries read the views from sql/schema/04_views.sql. Values from the request always
reach PostgreSQL as bound parameters. The only text added to a statement with an f-string
is a fixed fragment written in this file, never something the caller typed.
"""

from sqlalchemy import bindparam, text

from src.analytics.runner import ANALYTICS_DIR

# metric name used in the API -> column of the top-products query
PRODUCT_SORT_COLUMNS = {"revenue": "revenue", "profit": "profit", "units": "units_sold"}

STATUS_PRIORITY = """
    CASE i.stock_status
        WHEN 'Out of stock' THEN 1
        WHEN 'Stock-out risk' THEN 2
        ELSE 3
    END
"""


def as_dicts(result):
    return [dict(row) for row in result.mappings()]


def with_rank(rows):
    return [{"rank": rank, **row} for rank, row in enumerate(rows, start=1)]


def sales_conditions(start_date=None, end_date=None, location_id=None, category_id=None):
    """Build the WHERE clause for queries on vw_fact_sales (alias f, products alias p)."""
    conditions, params = [], {}
    if start_date:
        conditions.append("f.order_date >= :start_date")
        params["start_date"] = start_date
    if end_date:
        conditions.append("f.order_date <= :end_date")
        params["end_date"] = end_date
    if location_id:
        conditions.append("f.location_id = :location_id")
        params["location_id"] = location_id
    if category_id:
        conditions.append("p.category_id = :category_id")
        params["category_id"] = category_id
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    return where, params


def exists(connection, table, column, value):
    """True when the value is in the table. Table and column names are fixed by the caller."""
    query = text(f"SELECT EXISTS (SELECT 1 FROM {table} WHERE {column} = :value)")
    return connection.execute(query, {"value": value}).scalar_one()


def sales_summary(connection, start_date=None, end_date=None, location_id=None):
    where, params = sales_conditions(start_date, end_date, location_id)
    query = text(f"""
        SELECT
            COALESCE(SUM(f.net_revenue), 0) AS total_revenue,
            COALESCE(SUM(f.gross_profit), 0) AS total_profit,
            ROUND(100 * SUM(f.gross_profit) / NULLIF(SUM(f.net_revenue), 0), 1) AS margin_pct,
            COUNT(DISTINCT f.order_id) AS total_orders,
            COUNT(DISTINCT f.customer_id) AS total_customers,
            ROUND(SUM(f.net_revenue) / NULLIF(COUNT(DISTINCT f.order_id), 0), 2)
                AS avg_order_value,
            COALESCE(SUM(f.quantity), 0) AS units_sold
        FROM vw_fact_sales AS f
        {where}
    """)
    summary = dict(connection.execute(query, params).mappings().one())

    # stock is a snapshot, so the date filter does not apply to it
    stock_filter = "WHERE location_id = :location_id" if location_id else ""
    stock_query = text(
        f"SELECT COALESCE(SUM(inventory_value), 0) FROM vw_fact_inventory {stock_filter}"
    )
    stock_params = {"location_id": location_id} if location_id else {}
    summary["inventory_value"] = connection.execute(stock_query, stock_params).scalar_one()
    return summary


def monthly_sales(connection, start_date=None, end_date=None, location_id=None):
    where, params = sales_conditions(start_date, end_date, location_id)
    query = text(f"""
        WITH monthly AS (
            SELECT
                date_trunc('month', f.order_date)::date AS month,
                COUNT(DISTINCT f.order_id) AS orders,
                SUM(f.net_revenue) AS revenue,
                SUM(f.gross_profit) AS profit
            FROM vw_fact_sales AS f
            {where}
            GROUP BY 1
        )
        SELECT
            month,
            orders,
            revenue,
            profit,
            ROUND(100 * profit / NULLIF(revenue, 0), 1) AS margin_pct,
            ROUND(revenue / NULLIF(orders, 0), 2) AS avg_order_value,
            ROUND(100 * (revenue - LAG(revenue) OVER (ORDER BY month))
                  / NULLIF(LAG(revenue) OVER (ORDER BY month), 0), 1) AS mom_growth_pct
        FROM monthly
        ORDER BY month
    """)
    return as_dicts(connection.execute(query, params))


def top_products(
    connection, metric="revenue", limit=10, start_date=None, end_date=None, category_id=None
):
    where, params = sales_conditions(start_date, end_date, category_id=category_id)
    sort_column = PRODUCT_SORT_COLUMNS[metric]  # KeyError if the metric is not allowed
    query = text(f"""
        SELECT
            p.product_id,
            p.product_name,
            p.category_name,
            SUM(f.quantity) AS units_sold,
            SUM(f.net_revenue) AS revenue,
            SUM(f.gross_profit) AS profit,
            ROUND(100 * SUM(f.gross_profit) / NULLIF(SUM(f.net_revenue), 0), 1) AS margin_pct
        FROM vw_fact_sales AS f
        JOIN vw_dim_product AS p ON p.product_id = f.product_id
        {where}
        GROUP BY p.product_id, p.product_name, p.category_name
        ORDER BY {sort_column} DESC, p.product_id
        LIMIT :limit
    """)
    return with_rank(as_dicts(connection.execute(query, {**params, "limit": limit})))


def low_stock(connection, statuses, limit=50, location_id=None):
    location_filter = "AND i.location_id = :location_id" if location_id else ""
    params = {"statuses": list(statuses), "limit": limit}
    if location_id:
        params["location_id"] = location_id
    query = text(f"""
        SELECT
            p.product_id,
            p.product_name,
            p.category_name,
            i.location_id,
            l.location_name,
            i.quantity_on_hand,
            i.reorder_level,
            i.avg_daily_units,
            i.days_of_cover,
            i.lead_time_days,
            i.stock_status,
            i.suggested_order_qty
        FROM vw_fact_inventory AS i
        JOIN vw_dim_product AS p ON p.product_id = i.product_id
        JOIN vw_dim_location AS l ON l.location_id = i.location_id
        WHERE i.stock_status IN :statuses {location_filter}
        ORDER BY {STATUS_PRIORITY}, i.avg_daily_units * p.selling_price DESC, i.inventory_id
        LIMIT :limit
    """).bindparams(bindparam("statuses", expanding=True))
    return as_dicts(connection.execute(query, params))


def top_customers(connection, limit=10, start_date=None, end_date=None):
    where, params = sales_conditions(start_date, end_date)
    query = text(f"""
        SELECT
            c.customer_id,
            c.customer_name,
            c.customer_type,
            c.city,
            COUNT(DISTINCT f.order_id) AS orders,
            SUM(f.net_revenue) AS revenue,
            ROUND(100 * SUM(f.net_revenue) / SUM(SUM(f.net_revenue)) OVER (), 2)
                AS revenue_share_pct
        FROM vw_fact_sales AS f
        JOIN vw_dim_customer AS c ON c.customer_id = f.customer_id
        {where}
        GROUP BY c.customer_id, c.customer_name, c.customer_type, c.city
        ORDER BY revenue DESC, c.customer_id
        LIMIT :limit
    """)
    return with_rank(as_dicts(connection.execute(query, {**params, "limit": limit})))


def category_performance(connection):
    """Same query as sql/analytics/05_category_performance.sql, so there is one definition."""
    sql = (ANALYTICS_DIR / "05_category_performance.sql").read_text()
    return as_dicts(connection.execute(text(sql)))
