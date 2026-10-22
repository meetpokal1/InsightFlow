from fastapi import APIRouter, Depends
from sqlalchemy import text

from api.dependencies import get_connection
from api.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health", response_model=HealthResponse, summary="Check that the API and database are up"
)
def health(connection=Depends(get_connection)):
    connection.execute(text("SELECT 1"))
    return {"status": "ok"}
