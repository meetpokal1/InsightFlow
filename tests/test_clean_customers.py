import pandas as pd

from src.cleaning.customers import clean_customers
from tests.helpers import AS_OF, raw_table


def customer(customer_id, **changes):
    row = {
        "customer_id": customer_id,
        "customer_name": f"Customer {customer_id}",
        "email": f"{customer_id.lower()}@example.com",
        "phone": "98" + customer_id[1:].rjust(8, "0"),
        "city": "Pune",
        "customer_type": "Retail",
        "signup_date": "2024-01-15",
    }
    return row | changes


def test_customer_fields_are_standardised(log):
    raw = raw_table(
        "customers",
        customer(
            "c7",
            customer_name="PRIYA PATEL",
            email=" Priya.Patel@Example.COM ",
            phone="+91 98765 43210",
            city="bangalore",
            customer_type="WHOLESALER",
            signup_date="05/03/2025",
        ),
    )
    clean, _, _ = clean_customers(raw, AS_OF, log)
    row = clean.iloc[0]
    assert row["customer_id"] == "C7"
    assert row["customer_name"] == "Priya Patel"
    assert row["email"] == "priya.patel@example.com"
    assert row["phone"] == "9876543210"
    assert row["city"] == "Bengaluru"
    assert row["customer_type"] == "Wholesale"
    assert row["signup_date"] == pd.Timestamp("2025-03-05")


def test_customer_registered_twice_is_merged_by_email_into_the_earliest_signup(log):
    raw = raw_table(
        "customers",
        customer("C1", email="same@example.com", signup_date="2024-06-01"),
        customer("C2", email="Same@Example.com", signup_date="2024-02-01"),
        customer("C3"),
    )
    clean, _, duplicates = clean_customers(raw, AS_OF, log)
    assert duplicates == {"C1": "C2"}
    assert sorted(clean["customer_id"]) == ["C2", "C3"]
    assert log.count("customers", "duplicate_customers") == 1


def test_duplicates_with_the_same_signup_date_keep_the_lower_customer_id(log):
    raw = raw_table(
        "customers",
        customer("C9", email="same@example.com"),
        customer("C4", email="same@example.com"),
    )
    _, _, duplicates = clean_customers(raw, AS_OF, log)
    assert duplicates == {"C9": "C4"}


def test_customer_without_email_is_matched_by_name_and_phone(log):
    raw = raw_table(
        "customers",
        customer("C1", customer_name="Anita Rao", phone="9811111111", email=None),
        customer(
            "C2",
            customer_name="ANITA RAO",
            phone="+91 98111 11111",
            email=None,
            signup_date="2024-03-01",
        ),
    )
    clean, _, duplicates = clean_customers(raw, AS_OF, log)
    assert duplicates == {"C2": "C1"}
    assert clean["customer_id"].tolist() == ["C1"]


def test_same_name_with_a_different_phone_is_a_different_customer(log):
    raw = raw_table(
        "customers",
        customer("C1", customer_name="Anita Rao", phone="9811111111", email=None),
        customer("C2", customer_name="Anita Rao", phone="9822222222", email=None),
    )
    clean, _, duplicates = clean_customers(raw, AS_OF, log)
    assert duplicates == {}
    assert len(clean) == 2


def test_bad_values_are_set_to_missing_or_to_a_default(log):
    raw = raw_table(
        "customers",
        customer("C1", email="not-an-email"),
        customer("C2", signup_date="2027-01-01"),
        customer("C3", signup_date="31/02/2024"),
        customer("C4", customer_type="vip"),
    )
    clean, _, _ = clean_customers(raw, AS_OF, log)
    by_id = clean.set_index("customer_id")
    assert pd.isna(by_id.loc["C1", "email"])
    assert pd.isna(by_id.loc["C2", "signup_date"])
    assert pd.isna(by_id.loc["C3", "signup_date"])
    assert by_id.loc["C4", "customer_type"] == "Retail"
    assert log.count("customers", "invalid_email") == 1
    assert log.count("customers", "signup_date_in_future") == 1
    assert log.count("customers", "invalid_signup_date") == 1
    assert log.count("customers", "missing_or_unknown_customer_type") == 1


def test_exact_duplicates_are_dropped_and_rows_without_a_name_are_rejected(log):
    row = customer("C1")
    raw = raw_table("customers", row, row, customer("C2", customer_name=None))
    clean, rejected, _ = clean_customers(raw, AS_OF, log)
    assert clean["customer_id"].tolist() == ["C1"]
    assert rejected["reject_reason"].tolist() == ["missing_customer_name"]
    assert log.count("customers", "exact_duplicate_rows") == 1
