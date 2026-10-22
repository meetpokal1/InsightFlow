"""Steps that most of the table cleaners share."""

from src.tables import COLUMNS


def drop_exact_duplicates(df, table, log):
    """Drop rows that are identical in every column (the source row number is ignored).

    This runs on the raw values, before any cleaning, so rows that only differ in
    spelling or case are not counted here.
    """
    columns = [column for column in df.columns if column != "source_row"]
    duplicated = df.duplicated(subset=columns, keep="first")
    log.add(table, "exact_duplicate_rows", duplicated.sum(), "dropped")
    return df[~duplicated]


def drop_duplicate_keys(df, table, key, log, quarantine):
    """Remove repeated keys after the values have been standardised.

    Rows that became identical are dropped. Rows that still disagree with each other
    are quarantined, because we cannot tell which one is right.
    """
    identical = df.duplicated(subset=COLUMNS[table], keep="first")
    log.add(table, "duplicates_after_standardising", identical.sum(), "dropped")
    df = df[~identical]
    return quarantine.reject(df, df.duplicated(subset=key, keep="first"), f"conflicting_{key}")


def finish(df, table):
    """Keep only the columns of the data model, in order."""
    return df[COLUMNS[table]].reset_index(drop=True)
