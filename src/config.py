"""Project settings, read from environment variables (and an optional .env file)."""

import os
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# values already set in the real environment win over the .env file
load_dotenv(PROJECT_ROOT / ".env")


def _path_from_env(name: str, default: str) -> Path:
    path = Path(os.getenv(name, default))
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    database_url_override: str | None
    raw_data_dir: Path
    processed_data_dir: Path
    as_of_date: date | None
    log_level: str

    @property
    def database_url(self) -> str | URL:
        if self.database_url_override:
            return self.database_url_override
        # URL.create escapes special characters in the password
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Read the settings once. Tests can call get_settings.cache_clear() to re-read them."""
    as_of = os.getenv("AS_OF_DATE")
    return Settings(
        db_host=os.getenv("DB_HOST", "localhost"),
        db_port=int(os.getenv("DB_PORT", "5432")),
        db_name=os.getenv("DB_NAME", "sales_intelligence"),
        db_user=os.getenv("DB_USER", "sales_user"),
        db_password=os.getenv("DB_PASSWORD", ""),
        database_url_override=os.getenv("DATABASE_URL") or None,
        raw_data_dir=_path_from_env("RAW_DATA_DIR", "data/raw"),
        processed_data_dir=_path_from_env("PROCESSED_DATA_DIR", "data/processed"),
        as_of_date=date.fromisoformat(as_of) if as_of else None,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
