"""The full ETL run: read the raw files, clean and check them, save them, load PostgreSQL."""

import logging
import time
from dataclasses import dataclass
from datetime import date

import pandas as pd

from src.cleaning.clean_all import clean_all_tables
from src.cleaning.quality import QualityLog
from src.cleaning.validators import assert_valid
from src.config import get_settings
from src.database.connection import create_schema, drop_schema, get_engine
from src.database.loader import load_quality_log, load_tables, verify_row_counts
from src.ingestion.loader import load_raw_tables
from src.ingestion.profiling import profile_tables

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    clean: dict
    rejected: dict
    quality_log: pd.DataFrame
    profile: pd.DataFrame
    raw: dict | None = None


def clean_raw_files(raw_dir, as_of):
    """Read the raw files, profile them, clean them and check the result."""
    raw = load_raw_tables(raw_dir)
    profile = profile_tables(raw)
    log = QualityLog()
    clean, rejected = clean_all_tables(raw, as_of, log)
    assert_valid(clean)  # stops the pipeline before anything reaches the database
    return PipelineResult(clean, rejected, log.to_frame(), profile, raw)


def save_outputs(result, processed_dir):
    """Write the cleaned tables, the rejected rows, the quality log and the profile as CSV."""
    rejected_dir = processed_dir / "rejected"
    rejected_dir.mkdir(parents=True, exist_ok=True)
    for old_file in rejected_dir.glob("*_rejected.csv"):
        old_file.unlink()  # do not leave files from an earlier run behind

    for name, df in result.clean.items():
        df.to_csv(processed_dir / f"{name}.csv", index=False)
    for name, df in result.rejected.items():
        if len(df):
            df.to_csv(rejected_dir / f"{name}_rejected.csv", index=False)
    result.quality_log.to_csv(processed_dir / "data_quality_report.csv", index=False)
    result.profile.to_csv(processed_dir / "raw_data_profile.csv", index=False)


def run_pipeline(
    raw_dir=None,
    processed_dir=None,
    as_of=None,
    load_to_db=True,
    reset_schema=False,
    engine=None,
):
    settings = get_settings()
    raw_dir = raw_dir or settings.raw_data_dir
    processed_dir = processed_dir or settings.processed_data_dir
    as_of = as_of or settings.as_of_date or date.today()
    started = time.perf_counter()

    logger.info("Step 1/3: read and clean %s (orders dated after %s are invalid)", raw_dir, as_of)
    result = clean_raw_files(raw_dir, as_of)

    logger.info("Step 2/3: save the cleaned files to %s", processed_dir)
    save_outputs(result, processed_dir)

    if load_to_db:
        logger.info("Step 3/3: load PostgreSQL")
        engine = engine or get_engine()
        if reset_schema:
            drop_schema(engine)
        create_schema(engine)
        load_tables(engine, result.clean)
        load_quality_log(engine, result.quality_log)
        verify_row_counts(engine, result.clean)
    else:
        logger.info("Step 3/3: skipped, the database was not loaded")

    logger.info("Pipeline finished in %.1f seconds", time.perf_counter() - started)
    return result
