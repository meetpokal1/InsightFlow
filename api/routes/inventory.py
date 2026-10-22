from fastapi import APIRouter, Depends, Query

from api.dependencies import get_connection, require_known
from api.schemas.common import ErrorResponse
from api.schemas.inventory import LowStockItem, RiskStatus
from src.analytics import queries

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get(
    "/low-stock",
    response_model=list[LowStockItem],
    summary="Products that need restocking",
    responses={404: {"model": ErrorResponse, "description": "Unknown location_id"}},
)
def low_stock(
    status: list[RiskStatus] | None = Query(
        None, description="Stock statuses to include. All three are returned when left out."
    ),
    location_id: str | None = Query(None, description="Only this location", max_length=20),
    limit: int = Query(50, ge=1, le=500, description="How many rows to return"),
    connection=Depends(get_connection),
):
    """Out of stock first, then stock that runs out before a supplier could deliver."""
    require_known(connection, "locations", "location_id", location_id, "location_id")
    statuses = [item.value for item in status or list(RiskStatus)]
    return queries.low_stock(connection, statuses, limit, location_id)
