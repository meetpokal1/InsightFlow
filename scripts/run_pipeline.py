"""Run the whole pipeline: raw files -> cleaning -> PostgreSQL.

Examples:
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --skip-db
    python scripts/run_pipeline.py --reset-schema --as-of 2026-10-01
"""

import argparse
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import get_settings  # noqa: E402
from src.logging_config import setup_logging  # noqa: E402
from src.pipeline import run_pipeline  # noqa: E402


def main():
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Clean the raw files and load PostgreSQL")
    parser.add_argument("--raw-dir", type=Path, default=settings.raw_data_dir)
    parser.add_argument("--processed-dir", type=Path, default=settings.processed_data_dir)
    parser.add_argument("--as-of", type=date.fromisoformat, help="YYYY-MM-DD, default is today")
    parser.add_argument("--skip-db", action="store_true", help="only clean, do not load PostgreSQL")
    parser.add_argument("--reset-schema", action="store_true", help="drop and recreate the tables")
    args = parser.parse_args()

    setup_logging(settings.log_level)
    result = run_pipeline(
        raw_dir=args.raw_dir,
        processed_dir=args.processed_dir,
        as_of=args.as_of,
        load_to_db=not args.skip_db,
        reset_schema=args.reset_schema,
    )

    print("\nRows per table (clean / rejected):")
    for name, df in result.clean.items():
        print(f"  {name:12s} {len(df):7d} / {len(result.rejected[name])}")


if __name__ == "__main__":
    main()
