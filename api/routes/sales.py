from fastapi import APIRouter, Depends, Query

from api.dependencies import DateRange, get_connection, get_date_range, require_known
from api.schemas.common import ErrorResponse
from api.schemas.sales import MonthlySales, SalesSummary
from src.analytics import queries

router = APIRouter(prefix="/sales", tags=["Sales"])

LOCATION_FILTER = Query(None, description="Only this location, for example L01", max_length=20)


@router.get(
    "/summary",
    response_model=SalesSummary,
    summary="Headline sales numbers",
    responses={404: {"model": ErrorResponse, "description": "Unknown location_id"}},
)
def sales_summary(
    dates: DateRange = Depends(get_date_range),
    location_id: str | None = LOCATION_FILTER,
    connection=Depends(get_connection),
):
    """Revenue, profit, orders, customers and average order value for completed orders."""
    require_known(connection, "locations", "location_id", location_id, "location_id")
    return queries.sales_summary(connection, dates.start_date, dates.end_date, location_id)


@router.get(
    "/monthly",
    response_model=list[MonthlySales],
    summary="Sales by month",
    responses={404: {"model": ErrorResponse, "description": "Unknown location_id"}},
)
def monthly_sales(
    dates: DateRange = Depends(get_date_range),
    location_id: str | None = LOCATION_FILTER,
    connection=Depends(get_connection),
):
    """One row per month with revenue, profit, margin and growth against the previous month."""
    require_known(connection, "locations", "location_id", location_id, "location_id")
    return queries.monthly_sales(connection, dates.start_date, dates.end_date, location_id)
