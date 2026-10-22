import pandas as pd
import pytest

from src.cleaning.parsing import parse_dates, to_number


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1299", 1299.0),
        ("1,299.00", 1299.0),
        ("Rs 1,299", 1299.0),
        ("7 days", 7.0),
        ("5%", 5.0),
        ("-4", -4.0),
        ("12.5", 12.5),
    ],
)
def test_to_number_reads_the_first_number_in_the_text(text, expected):
    assert to_number(pd.Series([text])).iloc[0] == expected


def test_to_number_gives_nan_when_there_is_no_number():
    result = to_number(pd.Series(["abc", "", None]))
    assert result.isna().all()
    assert result.dtype == "float64"


def test_parse_dates_reads_every_supported_format():
    dates = pd.Series(["2025-03-05", "2025-03-05 14:30:00", "05/03/2025", "05-Mar-2025"])
    assert (parse_dates(dates) == pd.Timestamp("2025-03-05")).all()


def test_parse_dates_reads_slash_dates_day_first():
    assert parse_dates(pd.Series(["03/04/2025"])).iloc[0] == pd.Timestamp("2025-04-03")


@pytest.mark.parametrize("text", ["2025-02-30", "31/04/2025", "13/13/2025", "not a date", ""])
def test_parse_dates_rejects_dates_that_do_not_exist(text):
    assert parse_dates(pd.Series([text])).isna().all()
