"""Write the views and the calendar table that Power BI reads to CSV files.

Use it when Power BI cannot connect to PostgreSQL directly. The files go to powerbi/data
and are read with the queries in powerbi/power_query.md.

Examples:
    python scripts/export_powerbi_data.py
    python scripts/export_powerbi_data.py --out C:/temp/powerbi_data
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import PROJECT_ROOT, get_settings  # noqa: E402
from src.database.connection import get_engine  # noqa: E402
from src.logging_config import setup_logging  # noqa: E402

POWERBI_TABLES = [
    "vw_fact_sales",
    "vw_fact_inventory",
    "vw_dim_product",
    "vw_dim_customer",
    "vw_dim_location",
    "dim_date",
]


def export_tables(engine, out_dir):
    """Write one CSV per table or view and return {name: number of rows}."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name in POWERBI_TABLES:
        df = pd.read_sql_query(f"SELECT * FROM {name}", engine)
        df.to_csv(out_dir / f"{name}.csv", index=False)
        counts[name] = len(df)
    return counts


def main():
    parser = argparse.ArgumentParser(description="Export the Power BI tables to CSV files")
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "powerbi" / "data")
    args = parser.parse_args()

    setup_logging(get_settings().log_level)
    counts = export_tables(get_engine(), args.out)
    for name, rows in counts.items():
        print(f"  {name:20s} {rows:7d} rows")
    print(f"Files written to {args.out}")


if __name__ == "__main__":
    main()
