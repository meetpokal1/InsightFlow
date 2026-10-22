"""Run the analytics queries in sql/analytics/ and show or export the results.

Examples:
    python scripts/run_analytics.py
    python scripts/run_analytics.py --only 05 11
    python scripts/run_analytics.py --export
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.analytics.runner import list_queries, run_query  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.database.connection import get_engine  # noqa: E402
from src.logging_config import setup_logging  # noqa: E402


def main():
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run the SQL analytics queries")
    parser.add_argument("--only", nargs="+", metavar="NUMBER", help="query numbers, e.g. 05 11")
    parser.add_argument("--rows", type=int, default=12, help="rows to print per query")
    parser.add_argument("--export", action="store_true", help="also write each result to a CSV")
    parser.add_argument(
        "--export-dir", type=Path, default=settings.processed_data_dir / "analytics"
    )
    args = parser.parse_args()

    setup_logging(settings.log_level)
    engine = get_engine()
    pd.set_option("display.width", 200, "display.max_columns", 30)

    for path in list_queries():
        if args.only and path.stem[:2] not in args.only:
            continue
        result = run_query(engine, path)
        print(f"\n=== {path.stem} ({len(result)} rows) ===")
        print(result.head(args.rows).to_string(index=False))
        if args.export:
            args.export_dir.mkdir(parents=True, exist_ok=True)
            result.to_csv(args.export_dir / f"{path.stem}.csv", index=False)


if __name__ == "__main__":
    main()
