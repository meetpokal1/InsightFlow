"""Parse messy numbers and dates that arrive as text."""

import pandas as pd

from src.cleaning.rules import DATE_FORMATS
from src.cleaning.text import clean_text

NUMBER_PATTERN = r"(-?\d+(?:\.\d+)?)"


def to_number(series):
    """Convert text such as '1,299.00', 'Rs 1,299', '7 days' or '5%' to a float.

    The first number found in the text is used. Anything without a number becomes NaN.
    """
    text = series.astype("string").str.replace(",", "", regex=False)
    numbers = pd.to_numeric(text.str.extract(NUMBER_PATTERN, expand=False), errors="coerce")
    return numbers.astype("float64")


def parse_dates(series, formats=None):
    """Parse dates written in a few known formats. Invalid dates become NaT.

    Every format is matched strictly, so '2025-02-30' is invalid instead of being
    rolled over into March.
    """
    text = clean_text(series)
    result = pd.Series(pd.NaT, index=text.index, dtype="datetime64[ns]")
    for fmt in formats or DATE_FORMATS:
        parsed = pd.to_datetime(text, format=fmt, errors="coerce").astype("datetime64[ns]")
        result = result.fillna(parsed)
    return result.dt.normalize()
