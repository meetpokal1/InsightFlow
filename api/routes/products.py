from fastapi import APIRouter, Depends, Query

from api.dependencies import DateRange, get_connection, get_date_range, require_known
from api.schemas.common import ErrorResponse
from api.schemas.products import ProductMetric, TopProduct
from src.analytics import queries

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "/top",
    response_model=list[TopProduct],
    summary="Best selling products",
    responses={404: {"model": ErrorResponse, "description": "Unknown category_id"}},
)
def top_products(
    metric: ProductMetric = Query(ProductMetric.revenue, description="What to rank by"),
    limit: int = Query(10, ge=1, le=100, description="How many products to return"),
    category_id: str | None = Query(
        None, description="Only this category, for example CAT01", max_length=20
    ),
    dates: DateRange = Depends(get_date_range),
    connection=Depends(get_connection),
):
    """Products ranked by revenue, profit or units sold, for completed orders."""
    require_known(connection, "categories", "category_id", category_id, "category_id")
    return queries.top_products(
        connection, metric.value, limit, dates.start_date, dates.end_date, category_id
    )
