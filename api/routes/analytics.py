from fastapi import APIRouter, Depends

from api.dependencies import get_connection
from api.schemas.analytics import CategoryPerformance
from src.analytics import queries

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/category-performance",
    response_model=list[CategoryPerformance],
    summary="Revenue, margin and trend per category",
)
def category_performance(connection=Depends(get_connection)):
    """Compares the last 12 months with the 12 months before, per category."""
    return queries.category_performance(connection)
