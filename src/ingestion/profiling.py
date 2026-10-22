"""A quick look at the raw tables before anything is cleaned."""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def profile_table(df, table):
    """One row per column: missing values, distinct values, and how many look like numbers.

    plain_number_pct only counts values pandas can read as a number as they are, so
    a price column written as '1,299.00' scores lower than 100 and needs cleaning.
    """
    data = df.drop(columns="source_row", errors="ignore")
    filled = data.notna().sum()
    numeric = data.apply(lambda column: pd.to_numeric(column, errors="coerce").notna().sum())
    return pd.DataFrame(
        {
            "table_name": table,
            "column_name": data.columns,
            "rows": len(data),
            "missing": (len(data) - filled).to_numpy(),
            "missing_pct": (100 * (len(data) - filled) / max(len(data), 1)).round(1).to_numpy(),
            "distinct": data.nunique().to_numpy(),
            "plain_number_pct": (100 * numeric / filled.where(filled > 0)).round(1).to_numpy(),
        }
    )


def profile_tables(tables):
    profile = pd.concat([profile_table(df, name) for name, df in tables.items()], ignore_index=True)
    for table, rows in profile.groupby("table_name", sort=False):
        columns_with_gaps = rows.loc[rows["missing"] > 0, "column_name"].tolist()
        logger.info(
            "%s: %d rows, columns with missing values: %s",
            table,
            rows["rows"].iloc[0],
            columns_with_gaps or "none",
        )
    return profile
