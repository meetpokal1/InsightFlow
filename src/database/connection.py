"""Database connection and a helper to run the SQL files in sql/schema/."""

from pathlib import Path

from sqlalchemy import create_engine

from src.config import PROJECT_ROOT, get_settings
from src.tables import TABLE_LOAD_ORDER

SCHEMA_DIR = PROJECT_ROOT / "sql" / "schema"

# tables that are not part of the cleaned data model
EXTRA_TABLES = ["etl_quality_log", "dim_date"]


def get_engine(database_url=None):
    return create_engine(database_url or get_settings().database_url, pool_pre_ping=True)


def run_sql_file(engine, path):
    """Run all the statements in one .sql file inside a single transaction."""
    with engine.begin() as connection:
        connection.exec_driver_sql(
            Path(path).read_text(encoding="utf-8"),
            execution_options={"no_parameters": True},
        )


def create_schema(engine, schema_dir=SCHEMA_DIR):
    """Create the tables, indexes, calendar and views. The files are safe to run again."""
    for path in sorted(Path(schema_dir).glob("*.sql")):
        run_sql_file(engine, path)


def drop_schema(engine):
    """Delete this project's tables (the views that depend on them go with them)."""
    with engine.begin() as connection:
        for table in [*reversed(TABLE_LOAD_ORDER), *EXTRA_TABLES]:
            connection.exec_driver_sql(
                f"DROP TABLE IF EXISTS {table} CASCADE",
                execution_options={"no_parameters": True},
            )
