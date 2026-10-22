"""The export for Power BI writes every table and view with all of its rows and columns."""

import pandas as pd
import pytest

from scripts.export_powerbi_data import POWERBI_TABLES, export_tables

pytestmark = pytest.mark.db


def test_every_powerbi_table_is_exported_with_all_rows_and_columns(database, tmp_path):
    counts = export_tables(database, tmp_path)

    assert list(counts) == POWERBI_TABLES
    for name in POWERBI_TABLES:
        in_database = pd.read_sql_query(f"SELECT * FROM {name}", database)
        exported = pd.read_csv(tmp_path / f"{name}.csv")
        assert counts[name] == len(in_database) == len(exported), name
        assert list(exported.columns) == list(in_database.columns), name
