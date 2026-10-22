"""Run the SQL files in sql/analytics/ and return their results as DataFrames."""

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.config import PROJECT_ROOT

ANALYTICS_DIR = PROJECT_ROOT / "sql" / "analytics"


def list_queries(directory=ANALYTICS_DIR):
    return sorted(Path(directory).glob("*.sql"))


def run_query(engine, path):
    with engine.connect() as connection:
        return pd.read_sql_query(text(Path(path).read_text()), connection)


def run_all(engine, directory=ANALYTICS_DIR):
    """Return {file name without extension: result} for every analytics query."""
    return {path.stem: run_query(engine, path) for path in list_queries(directory)}
