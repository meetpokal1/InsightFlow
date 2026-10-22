import pandas as pd

from src.cleaning.quality import LOG_COLUMNS, QualityLog, Quarantine


def test_quarantine_takes_the_rows_out_and_records_why(log):
    quarantine = Quarantine("orders", log)
    df = pd.DataFrame({"order_id": ["O1", "O2", "O3"]})
    kept = quarantine.reject(df, df["order_id"] == "O2", "bad_row")
    assert kept["order_id"].tolist() == ["O1", "O3"]
    assert quarantine.total == 1
    assert quarantine.frame()["order_id"].tolist() == ["O2"]
    assert quarantine.frame()["reject_reason"].tolist() == ["bad_row"]
    assert log.count("orders", "bad_row") == 1


def test_quarantine_treats_missing_values_in_the_mask_as_false(log):
    quarantine = Quarantine("orders", log)
    df = pd.DataFrame({"order_id": ["O1", "O2"]})
    mask = pd.Series([True, pd.NA], dtype="boolean")
    assert quarantine.reject(df, mask, "bad_row")["order_id"].tolist() == ["O2"]


def test_the_log_ignores_problems_that_affected_no_rows():
    log = QualityLog()
    log.add("orders", "nothing_wrong", 0, "none")
    assert log.to_frame().empty
    assert list(log.to_frame().columns) == LOG_COLUMNS


def test_the_log_adds_up_rows_per_table_and_issue(log):
    log.add("orders", "invalid_order_date", 3, "rejected")
    log.add("orders", "invalid_order_date", 2, "rejected")
    log.add("customers", "invalid_order_date", 7, "rejected")
    assert log.count("orders", "invalid_order_date") == 5
    assert log.to_frame()["rows_affected"].sum() == 12
