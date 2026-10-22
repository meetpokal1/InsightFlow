"""Bookkeeping for data problems: what was wrong, how many rows, what we did about it."""

import logging
from dataclasses import asdict, dataclass

import pandas as pd

logger = logging.getLogger(__name__)

LOG_COLUMNS = ["table_name", "issue", "rows_affected", "action"]


@dataclass(frozen=True)
class QualityIssue:
    table_name: str
    issue: str
    rows_affected: int
    action: str


class QualityLog:
    """One entry per issue found. It is saved as the etl_quality_log table."""

    def __init__(self):
        self.issues = []

    def add(self, table, issue, rows, action):
        rows = int(rows)
        if rows <= 0:
            return
        self.issues.append(QualityIssue(table, issue, rows, action))
        logger.info("[%s] %s: %d rows -> %s", table, issue, rows, action)

    def count(self, table, issue):
        return sum(
            i.rows_affected for i in self.issues if i.table_name == table and i.issue == issue
        )

    def to_frame(self):
        if not self.issues:
            return pd.DataFrame(columns=LOG_COLUMNS)
        return pd.DataFrame([asdict(i) for i in self.issues])[LOG_COLUMNS]


class Quarantine:
    """Holds the rows of one table that were rejected, together with the reason."""

    def __init__(self, table, log):
        self.table = table
        self.log = log
        self._parts = []

    def reject(self, df, mask, reason):
        """Move the rows where mask is True out of df and return the remaining rows."""
        mask = pd.Series(mask, index=df.index).fillna(False).astype(bool)
        bad = df[mask]
        if len(bad):
            self._parts.append(bad.assign(reject_reason=reason))
            self.log.add(self.table, reason, len(bad), "rejected")
        return df[~mask]

    @property
    def total(self):
        return sum(len(part) for part in self._parts)

    def frame(self):
        if not self._parts:
            return pd.DataFrame(columns=["reject_reason"])
        return pd.concat(self._parts, ignore_index=True)
