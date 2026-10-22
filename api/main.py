"""The FastAPI application.

Run it with:  uvicorn api.main:app --reload
Swagger UI is then at http://localhost:8000/docs
"""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from api.routes import analytics, customers, health, inventory, products, sales
from src.config import get_settings
from src.database.connection import get_engine
from src.logging_config import setup_logging

logger = logging.getLogger("api")

DESCRIPTION = """
Read-only access to the sales and inventory numbers in PostgreSQL.
All sales figures use completed orders only. Money is in rupees.
"""

TAGS = [
    {"name": "Sales", "description": "Revenue, profit and orders"},
    {"name": "Products", "description": "Best selling products"},
    {"name": "Inventory", "description": "Stock levels and restocking"},
    {"name": "Customers", "description": "Highest spending customers"},
    {"name": "Analytics", "description": "Category performance"},
    {"name": "Health", "description": "Service status"},
]


def create_app(engine=None):
    """Build the app. Tests pass their own engine, otherwise one is made from the settings."""

    @asynccontextmanager
    async def lifespan(app):
        setup_logging(get_settings().log_level)
        owns_engine = engine is None
        app.state.engine = get_engine() if owns_engine else engine
        logger.info("API started")
        yield
        if owns_engine:
            app.state.engine.dispose()

    app = FastAPI(
        title="Sales and Inventory Intelligence API",
        description=DESCRIPTION,
        version="1.0.0",
        openapi_tags=TAGS,
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def log_requests(request, call_next):
        started = time.perf_counter()
        response = await call_next(request)
        milliseconds = (time.perf_counter() - started) * 1000
        logger.info(
            "%s %s -> %d (%.0f ms)",
            request.method,
            request.url.path,
            response.status_code,
            milliseconds,
        )
        return response

    @app.exception_handler(OperationalError)
    async def database_unavailable(request, exc):
        reason = str(exc.orig).splitlines()[0]
        logger.error("Database unavailable for %s: %s", request.url.path, reason)
        return JSONResponse(status_code=503, content={"detail": "The database is not available"})

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        logger.exception("Database error for %s", request.url.path)
        return JSONResponse(status_code=500, content={"detail": "The database query failed"})

    for module in (sales, products, inventory, customers, analytics, health):
        app.include_router(module.router)
    return app


app = create_app()
