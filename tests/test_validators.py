import pandas as pd
import pytest

from src.cleaning.validators import (
    DataValidationError,
    assert_valid,
    find_orphans,
    is_valid_email,
    validate_dataset,
)
from tests.helpers import tiny_dataset


def test_is_valid_email():
    emails = pd.Series(
        ["a@b.com", "first.last+tag@mail.example.org", "no-at-sign.com", "a@b", "a @b.com", None]
    )
    assert is_valid_email(emails).tolist() == [True, True, False, False, False, False]


def test_find_orphans_ignores_missing_values():
    child = pd.Series(["P1", "P9", None])
    assert find_orphans(child, ["P1", "P2"]).tolist() == [False, True, False]


def test_a_valid_dataset_has_no_problems():
    assert validate_dataset(tiny_dataset()) == []


def test_columns_that_do_not_match_the_data_model_are_reported():
    tables = tiny_dataset()
    tables["customers"] = tables["customers"].drop(columns="phone")
    assert validate_dataset(tables) == ["customers: columns do not match the data model"]


def test_duplicate_primary_key_is_reported():
    tables = tiny_dataset()
    tables["products"] = pd.concat([tables["products"]] * 2, ignore_index=True)
    assert validate_dataset(tables) == ["products: 1 duplicate values in product_id"]


def test_missing_required_value_is_reported():
    tables = tiny_dataset()
    tables["orders"].loc[0, "payment_method"] = None
    assert validate_dataset(tables) == [
        "orders: 1 missing values in required column payment_method"
    ]


def test_foreign_key_without_a_parent_row_is_reported():
    tables = tiny_dataset()
    tables["order_items"].loc[0, "product_id"] = "P9999"
    assert validate_dataset(tables) == ["order_items.product_id: 1 values not found in products"]


@pytest.mark.parametrize(
    "table, column, value, rule",
    [
        ("inventory", "quantity_on_hand", -1, "quantity_on_hand is not negative"),
        ("order_items", "quantity", 0, "quantity is between 1 and 500"),
        ("order_items", "quantity", 501, "quantity is between 1 and 500"),
        ("order_items", "discount_pct", 101.0, "discount_pct is between 0 and 100"),
        ("products", "cost_price", 150.0, "cost_price is between 0 and selling_price"),
        ("orders", "order_status", "Pending", "order_status is a known status"),
        ("locations", "region", "Moon", "region is a known region"),
    ],
)
def test_value_rules_are_checked(table, column, value, rule):
    tables = tiny_dataset()
    tables[table].loc[0, column] = value
    problems = validate_dataset(tables)
    assert problems == [f"{table}: 1 rows where {rule} is not true"]


def test_assert_valid_stops_the_pipeline_with_every_problem_listed():
    tables = tiny_dataset()
    tables["order_items"].loc[0, "product_id"] = "P9999"
    tables["inventory"].loc[0, "quantity_on_hand"] = -5
    with pytest.raises(DataValidationError) as error:
        assert_valid(tables)
    assert "not found in products" in str(error.value)
    assert "quantity_on_hand is not negative" in str(error.value)


def test_assert_valid_accepts_a_valid_dataset():
    assert_valid(tiny_dataset())
