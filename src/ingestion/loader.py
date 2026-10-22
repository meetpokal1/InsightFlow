"""Read the raw CSV and Excel files."""

import logging

import pandas as pd

from src.tables import COLUMNS, RAW_ONLY_COLUMNS, TABLE_LOAD_ORDER

logger = logging.getLogger(__name__)


def find_raw_file(raw_dir, table):
    for extension in (".csv", ".xlsx"):
        path = raw_dir / f"{table}{extension}"
        if path.exists():
            return path
    raise FileNotFoundError(f"Neither {table}.csv nor {table}.xlsx exists in {raw_dir}")


def read_raw_table(path):
    """Read a file with every column as text, so nothing is guessed on the way in.

    The extra source_row column is the row number in the original file (the header is
    row 1). It lets a rejected record be traced back to the line it came from.
    """
    options = {"dtype": str, "keep_default_na": False, "na_values": [""]}
    if path.suffix == ".xlsx":
        df = pd.read_excel(path, **options)
    else:
        df = pd.read_csv(path, **options)
    df.insert(0, "source_row", range(2, len(df) + 2))
    return df


def check_columns(df, table, path):
    """Stop with a clear message when a file does not have the columns the cleaner needs."""
    expected = COLUMNS[table] + RAW_ONLY_COLUMNS.get(table, [])
    missing = [column for column in expected if column not in df.columns]
    if missing:
        found = ", ".join(df.columns[1:])  # the first column is source_row
        raise ValueError(f"{path.name} has no column {', '.join(missing)} (found: {found})")


def load_raw_tables(raw_dir):
    """Return {table name: raw DataFrame} for all eight tables."""
    tables = {}
    for table in TABLE_LOAD_ORDER:
        path = find_raw_file(raw_dir, table)
        tables[table] = read_raw_table(path)
        check_columns(tables[table], table, path)
        logger.info("Read %s (%d rows)", path.name, len(tables[table]))
    return tables
