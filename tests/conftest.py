"""Fixtures shared by the tests.

Tests that need PostgreSQL are marked `db`. They use a separate database (DB_NAME with
"_test" added, or TEST_DB_NAME) and are skipped when it cannot be reached, so the real
data is never touched.
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from src.cleaning.quality import QualityLog
from src.config import get_settings
from src.pipeline import clean_raw_files, run_pipeline
from src.synthetic.build import build_raw_dataset
from src.synthetic.generator import SyntheticConfig
from tests.helpers import AS_OF


@pytest.fixture
def log():
    return QualityLog()


@pytest.fixture(scope="session")
def raw_data(tmp_path_factory):
    """A small messy dataset (200 customers) written to a temporary folder.

    Returns the folder and the manifest that says what was damaged and what the clean
    totals are.
    """
    raw_dir = tmp_path_factory.mktemp("raw")
    manifest = build_raw_dataset(raw_dir, SyntheticConfig(n_customers=200))
    return raw_dir, manifest


@pytest.fixture(scope="session")
def cleaned(raw_data):
    """The small dataset after the cleaning step (nothing is written to a database)."""
    raw_dir, _ = raw_data
    return clean_raw_files(raw_dir, AS_OF)


@pytest.fixture(scope="session")
def db_engine():
    settings = get_settings()
    name = os.getenv("TEST_DB_NAME", f"{settings.db_name}_test")
    if name == settings.db_name:
        pytest.skip("TEST_DB_NAME must be a different database from DB_NAME")

    url = make_url(settings.database_url).set(database=name)
    engine = None
    try:
        engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
        engine.connect().close()
    except (OperationalError, ModuleNotFoundError, ImportError, Exception) as error:
        if engine:
            engine.dispose()
        reason = str(error).splitlines()[0]
        pytest.skip(f"test database {name} is not reachable: {reason}")
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def database(db_engine, raw_data, tmp_path_factory):
    """The small dataset loaded into the test database by the real pipeline."""
    raw_dir, _ = raw_data
    run_pipeline(
        raw_dir=raw_dir,
        processed_dir=tmp_path_factory.mktemp("processed"),
        as_of=AS_OF,
        reset_schema=True,
        engine=db_engine,
    )
    return db_engine
