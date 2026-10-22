"""The cleaning pipeline run on a small generated dataset where the problems are known."""

import pandas as pd
import pytest

from src.cleaning.validators import validate_dataset
from src.ingestion.loader import load_raw_tables
from src.pipeline import clean_raw_files, run_pipeline
from src.tables import TABLE_LOAD_ORDER
from tests.helpers import AS_OF, completed_sales_lines

# Problems injected into the raw files, and the name the quality log gives each one.
# A row with two problems is counted by the first rule that catches it, so the pipeline
# may report a few less than were injected, but never more.
LOGGED_AS = {
    "customers": {
        "exact_duplicate_rows": "exact_duplicate_rows",
        "duplicate_customers_new_id": "duplicate_customers",
        "invalid_signup_date": "invalid_signup_date",
        "missing_customer_type": "missing_or_unknown_customer_type",
    },
    "orders": {
        "exact_duplicate_rows": "exact_duplicate_rows",
        "invalid_order_date": "invalid_order_date",
        "future_order_date": "order_date_out_of_range",
        "unknown_customer_id": "unknown_customer_id",
        "missing_customer_id": "missing_customer_id",
        "unknown_location_id": "unknown_location_id",
        "missing_location_id": "missing_location_id",
        "missing_payment_method": "missing_or_unknown_payment_method",
        "orders_booked_under_duplicate_customer_id": "customer_id_of_duplicate_customer",
    },
    "order_items": {
        "exact_duplicate_rows": "exact_duplicate_rows",
        "invalid_product_id": "unknown_product_id",
        "negative_quantity": "negative_quantity",
        "zero_quantity": "zero_quantity",
        "missing_quantity": "missing_quantity",
        "quantity_outlier": "quantity_outlier",
        "missing_unit_price": "missing_unit_price",
        "unit_price_outlier": "unit_price_outlier",
        "missing_discount": "missing_discount",
        "invalid_discount": "invalid_discount",
    },
    "products": {
        "exact_duplicate_rows": "exact_duplicate_rows",
        "cost_price_greater_than_selling_price": "cost_price_above_selling_price",
        "missing_cost_price": "missing_cost_price",
    },
    "inventory": {
        "negative_quantity_on_hand": "negative_quantity_on_hand",
        "missing_reorder_level": "missing_reorder_level",
        "stale_duplicate_product_location_row": "stale_duplicate_stock_row",
        "invalid_product_id": "unknown_product_id",
    },
}
CASES = [
    (table, injected, logged_as)
    for table, issues in LOGGED_AS.items()
    for injected, logged_as in issues.items()
]


def logged(cleaned, table, issue):
    """Rows the quality log reports for one problem in one table."""
    log = cleaned.quality_log
    matches = (log["table_name"] == table) & (log["issue"] == issue)
    return int(log.loc[matches, "rows_affected"].sum())


def test_cleaned_tables_pass_every_validation_rule(cleaned):
    assert validate_dataset(cleaned.clean) == []


@pytest.mark.parametrize("table, injected_issue, logged_issue", CASES)
def test_the_pipeline_finds_the_problems_that_were_injected(
    cleaned, raw_data, table, injected_issue, logged_issue
):
    _, manifest = raw_data
    injected = manifest["injected_issues"][table][injected_issue]
    found = logged(cleaned, table, logged_issue)
    assert 0.9 * injected <= found <= injected


def test_lines_of_missing_orders_are_all_rejected(cleaned, raw_data):
    # also includes the lines of orders that were rejected for another reason
    _, manifest = raw_data
    injected = manifest["injected_issues"]["order_items"]["orphan_order_id"]
    assert logged(cleaned, "order_items", "order_not_found") >= injected


def test_every_raw_row_is_kept_rejected_merged_or_dropped_as_a_duplicate(cleaned, raw_data):
    raw_dir, _ = raw_data
    raw = load_raw_tables(raw_dir)
    for table in TABLE_LOAD_ORDER:
        removed = sum(
            logged(cleaned, table, issue)
            for issue in (
                "exact_duplicate_rows",
                "duplicates_after_standardising",
                "duplicate_customers",
            )
        )
        added = 1 if table == "categories" else 0  # the Uncategorized category is created
        kept = len(cleaned.clean[table]) - added
        assert kept + len(cleaned.rejected[table]) + removed == len(raw[table]), table


def test_customers_registered_twice_are_merged_back_to_the_real_number(cleaned, raw_data):
    _, manifest = raw_data
    assert len(cleaned.clean["customers"]) == manifest["ground_truth"]["customers"]


def test_recovered_revenue_is_close_to_the_revenue_of_the_clean_data(cleaned, raw_data):
    _, manifest = raw_data
    recovered = completed_sales_lines(cleaned.clean)["revenue"].sum()
    truth = manifest["ground_truth"]["completed_net_revenue"]
    # rejected rows cost a few percent of revenue; the rest has to be recovered
    assert 0.95 <= recovered / truth <= 1.01


def test_cleaning_the_same_files_twice_gives_the_same_result(cleaned, raw_data):
    raw_dir, _ = raw_data
    again = clean_raw_files(raw_dir, AS_OF)
    for table in TABLE_LOAD_ORDER:
        pd.testing.assert_frame_equal(cleaned.clean[table], again.clean[table])


def test_pipeline_writes_the_output_files_and_removes_old_rejected_files(raw_data, tmp_path):
    raw_dir, _ = raw_data
    old_file = tmp_path / "rejected" / "old_table_rejected.csv"
    old_file.parent.mkdir()
    old_file.write_text("left over from an earlier run")

    result = run_pipeline(raw_dir=raw_dir, processed_dir=tmp_path, as_of=AS_OF, load_to_db=False)

    for table in TABLE_LOAD_ORDER:
        assert len(pd.read_csv(tmp_path / f"{table}.csv")) == len(result.clean[table])
    assert (tmp_path / "data_quality_report.csv").exists()
    assert (tmp_path / "raw_data_profile.csv").exists()
    assert (tmp_path / "rejected" / "order_items_rejected.csv").exists()
    assert not old_file.exists()
