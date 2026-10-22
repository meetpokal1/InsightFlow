from fastapi import APIRouter, Depends, Query

from api.dependencies import DateRange, get_connection, get_date_range
from api.schemas.customers import TopCustomer
from src.analytics import queries

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("/top", response_model=list[TopCustomer], summary="Highest spending customers")
def top_customers(
    limit: int = Query(10, ge=1, le=100, description="How many customers to return"),
    dates: DateRange = Depends(get_date_range),
    connection=Depends(get_connection),
):
    """Customers ranked by revenue from completed orders."""
    return queries.top_customers(connection, limit, dates.start_date, dates.end_date)
