"""Load the cleaned tables into PostgreSQL."""

import logging

import pandas as pd
from sqlalchemy import text

from src.tables import TABLE_LOAD_ORDER

logger = logging.getLogger(__name__)

CHUNK_SIZE = 2000


def prepare_for_sql(df):
    """Turn timestamps into plain dates and every kind of missing value into None."""
    df = df.copy()
    for column in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[column]):
            df[column] = df[column].dt.date
    return df.astype(object).where(df.notna(), None)


def load_tables(engine, tables):
    """Replace the content of all tables in one transaction, so a failure changes nothing."""
    with engine.begin() as connection:
        names = ", ".join(TABLE_LOAD_ORDER)
        connection.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))
        for name in TABLE_LOAD_ORDER:
            prepare_for_sql(tables[name]).to_sql(
                name,
                connection,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=CHUNK_SIZE,
            )
            logger.info("Loaded %s (%d rows)", name, len(tables[name]))


def load_quality_log(engine, quality_log):
    """Append this run's data-quality findings to etl_quality_log."""
    if len(quality_log):
        quality_log.to_sql("etl_quality_log", engine, if_exists="append", index=False)


def verify_row_counts(engine, tables):
    """Compare the row count of each table in the database with what was loaded."""
    with engine.connect() as connection:
        for name in TABLE_LOAD_ORDER:
            in_database = connection.execute(text(f"SELECT COUNT(*) FROM {name}")).scalar_one()
            if in_database != len(tables[name]):
                raise RuntimeError(
                    f"{name}: loaded {len(tables[name])} rows but the table has {in_database}"
                )
    logger.info("Row counts in PostgreSQL match the cleaned data")
