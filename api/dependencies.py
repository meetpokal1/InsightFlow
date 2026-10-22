"""Dependencies shared by the routes."""

from dataclasses import dataclass
from datetime import date

from fastapi import HTTPException, Query, Request

from src.analytics.queries import exists


def get_connection(request: Request):
    """Open a database connection for one request and close it afterwards."""
    with request.app.state.engine.connect() as connection:
        yield connection


@dataclass
class DateRange:
    start_date: date | None
    end_date: date | None


def get_date_range(
    start_date: date | None = Query(None, description="First order date (YYYY-MM-DD)"),
    end_date: date | None = Query(None, description="Last order date (YYYY-MM-DD)"),
):
    """Read the optional date filter and reject a range that ends before it starts."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must not be after end_date")
    return DateRange(start_date, end_date)


def require_known(connection, table, column, value, label):
    """Raise 404 when a filter value (a location or category id) does not exist."""
    if value is not None and not exists(connection, table, column, value):
        raise HTTPException(status_code=404, detail=f"Unknown {label}: {value}")
