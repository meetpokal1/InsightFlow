import pandas as pd
import pytest

from src.cleaning.text import (
    clean_phone,
    clean_text,
    map_vocabulary,
    normalize_id,
    remap_ids,
    standardize_city,
    standardize_location_name,
    tidy_name,
)
from tests.helpers import as_list


def test_clean_text_trims_and_collapses_spaces():
    result = clean_text(pd.Series(["  Green   Tea ", "Rice"]))
    assert as_list(result) == ["Green Tea", "Rice"]


@pytest.mark.parametrize("value", ["", "   ", "N/A", "null", "None", "nan", "-"])
def test_clean_text_turns_null_like_strings_into_missing(value):
    assert clean_text(pd.Series([value])).isna().all()


def test_clean_text_can_change_case():
    series = pd.Series(["aBc dEf"])
    assert as_list(clean_text(series, case="title")) == ["Abc Def"]
    assert as_list(clean_text(series, case="upper")) == ["ABC DEF"]
    assert as_list(clean_text(series, case="lower")) == ["abc def"]


def test_normalize_id_removes_spaces_and_upper_cases():
    assert as_list(normalize_id(pd.Series([" p0012 ", "c 001", None]))) == ["P0012", "C001", None]


def test_tidy_name_only_fixes_names_written_in_a_single_case():
    names = pd.Series(
        [
            "PRIYA PATEL",
            "priya patel",
            "Priya PATEL",
            "crest consulting llp",
            "Crest Consulting LLP",
            "McDonald Traders",
        ]
    )
    assert as_list(tidy_name(names)) == [
        "Priya Patel",
        "Priya Patel",
        "Priya PATEL",
        "Crest Consulting LLP",
        "Crest Consulting LLP",
        "McDonald Traders",
    ]


def test_clean_phone_keeps_the_last_ten_digits():
    phones = pd.Series(["+91 98765 43210", "(022) 2345-6789", "98765-43210", "12345", None])
    assert as_list(clean_phone(phones)) == [
        "9876543210",
        "2223456789",
        "9876543210",
        None,
        None,
    ]


def test_map_vocabulary_ignores_case_and_spacing_and_flags_unknown_values():
    mapping = {"retail": "Retail", "wholesale": "Wholesale"}
    result = map_vocabulary(pd.Series([" RETAIL ", "Wholesale", "other", None]), mapping)
    assert as_list(result) == ["Retail", "Wholesale", None, None]


def test_standardize_city_uses_the_current_name():
    cities = pd.Series(["bangalore ", "MUMBAI", "Bombay", "new delhi", "nashik", None])
    assert as_list(standardize_city(cities)) == [
        "Bengaluru",
        "Mumbai",
        "Mumbai",
        "Delhi",
        "Nashik",
        None,
    ]


def test_standardize_location_name_replaces_old_city_names():
    names = pd.Series(["  Bangalore   Warehouse ", "DELHI WAREHOUSE"])
    assert as_list(standardize_location_name(names)) == ["Bengaluru Warehouse", "Delhi Warehouse"]


def test_remap_ids_only_changes_the_mapped_values():
    ids = pd.Series(["C2", "C1", "C3"])
    assert as_list(remap_ids(ids, {"C2": "C1"})) == ["C1", "C1", "C3"]
    assert as_list(remap_ids(ids, {})) == ["C2", "C1", "C3"]
