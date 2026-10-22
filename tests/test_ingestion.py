import pandas as pd
import pytest

from src.ingestion.loader import check_columns, find_raw_file, read_raw_table
from src.ingestion.profiling import profile_table


def test_csv_is_read_as_text_and_empty_cells_are_missing(tmp_path):
    path = tmp_path / "categories.csv"
    path.write_text("category_id,category_name\n007,Tea\n,\n")
    df = read_raw_table(path)
    assert df["category_id"].iloc[0] == "007"
    assert df["category_id"].isna().iloc[1]
    assert df["category_name"].isna().iloc[1]


def test_excel_is_read_the_same_way(tmp_path):
    path = tmp_path / "categories.xlsx"
    pd.DataFrame({"category_id": ["007", None], "category_name": ["Tea", "Coffee"]}).to_excel(
        path, index=False
    )
    df = read_raw_table(path)
    assert df["category_id"].iloc[0] == "007"
    assert df["category_id"].isna().iloc[1]


def test_source_row_is_the_line_number_in_the_original_file(tmp_path):
    path = tmp_path / "categories.csv"
    path.write_text("category_id,category_name\nA,One\nB,Two\nC,Three\n")
    assert read_raw_table(path)["source_row"].tolist() == [2, 3, 4]


def test_a_missing_raw_file_is_reported_by_name(tmp_path):
    with pytest.raises(FileNotFoundError, match="orders"):
        find_raw_file(tmp_path, "orders")


def test_a_missing_column_is_reported_with_the_columns_that_were_found(tmp_path):
    path = tmp_path / "categories.csv"
    path.write_text("category_id,name\nC1,Tea\n")
    message = r"categories.csv has no column category_name \(found: category_id, name\)"
    with pytest.raises(ValueError, match=message):
        check_columns(read_raw_table(path), "categories", path)


def test_the_orders_file_needs_the_order_total_column(tmp_path):
    path = tmp_path / "orders.csv"
    path.write_text("order_id,customer_id,location_id,order_date,order_status,payment_method\n")
    with pytest.raises(ValueError, match="no column order_total"):
        check_columns(read_raw_table(path), "orders", path)


def test_the_order_of_the_columns_does_not_matter(tmp_path):
    path = tmp_path / "categories.csv"
    path.write_text("category_name,category_id\nTea,C1\n")
    check_columns(read_raw_table(path), "categories", path)


def test_profile_counts_missing_values_and_plain_numbers():
    df = pd.DataFrame(
        {
            "source_row": [2, 3, 4, 5],
            "price": ["10", "1,200", None, "30"],
            "name": ["a", "b", "c", None],
        }
    )
    profile = profile_table(df, "demo").set_index("column_name")
    assert "source_row" not in profile.index
    assert profile.loc["price", "missing"] == 1
    assert profile.loc["price", "missing_pct"] == 25.0
    assert profile.loc["price", "plain_number_pct"] == pytest.approx(66.7, abs=0.1)
    assert profile.loc["name", "plain_number_pct"] == 0.0
