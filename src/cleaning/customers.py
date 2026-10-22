"""Cleaning for the customers table, including merging customers registered twice."""

import pandas as pd

from src.cleaning.common import drop_exact_duplicates, finish
from src.cleaning.parsing import parse_dates
from src.cleaning.quality import Quarantine
from src.cleaning.rules import CUSTOMER_TYPES, DEFAULT_CUSTOMER_TYPE
from src.cleaning.text import (
    clean_phone,
    clean_text,
    map_vocabulary,
    normalize_id,
    standardize_city,
    tidy_name,
)
from src.cleaning.validators import is_valid_email


def find_duplicate_customers(df):
    """Return {duplicate id: id to keep} for customers who are registered more than once.

    Two records are the same customer when they share an email address or, if that is
    missing, the same name and phone number. The record with the earliest sign-up date
    is kept, and ties go to the lower customer id.
    """
    ordered = df.sort_values(["signup_date", "customer_id"], na_position="last")
    duplicates = {}
    for keys in (["email"], ["customer_name", "phone"]):
        remaining = ordered[~ordered["customer_id"].isin(set(duplicates))]
        keep = remaining.groupby(keys)["customer_id"].transform("first")
        is_duplicate = (keep.notna() & (keep != remaining["customer_id"])).fillna(False)
        duplicates.update(
            zip(remaining.loc[is_duplicate, "customer_id"], keep[is_duplicate], strict=True)
        )
    return duplicates


def clean_customers(raw, as_of, log):
    """Return the clean customers, the rejected rows and {duplicate id: id that was kept}."""
    quarantine = Quarantine("customers", log)
    df = drop_exact_duplicates(raw, "customers", log)

    signup_text = clean_text(df["signup_date"])
    signup_date = parse_dates(signup_text)
    invalid_date = signup_text.notna() & signup_date.isna()
    log.add("customers", "invalid_signup_date", invalid_date.sum(), "set to missing")
    future_date = signup_date > pd.Timestamp(as_of)
    log.add("customers", "signup_date_in_future", future_date.sum(), "set to missing")

    df = df.assign(
        customer_id=normalize_id(df["customer_id"]),
        customer_name=tidy_name(df["customer_name"]),
        email=clean_text(df["email"], case="lower"),
        phone=clean_phone(df["phone"]),
        city=standardize_city(df["city"]),
        customer_type=map_vocabulary(df["customer_type"], CUSTOMER_TYPES),
        signup_date=signup_date.mask(future_date.fillna(False)),
    )
    df = quarantine.reject(df, df["customer_id"].isna(), "missing_customer_id")
    df = quarantine.reject(df, df["customer_name"].isna(), "missing_customer_name")
    df = quarantine.reject(df, df.duplicated("customer_id"), "duplicate_customer_id")

    bad_email = df["email"].notna() & ~is_valid_email(df["email"])
    log.add("customers", "invalid_email", bad_email.sum(), "set to missing")
    df = df.assign(email=df["email"].mask(bad_email))

    no_type = df["customer_type"].isna()
    log.add("customers", "missing_or_unknown_customer_type", no_type.sum(), "set to Retail")
    df = df.assign(customer_type=df["customer_type"].fillna(DEFAULT_CUSTOMER_TYPE))

    duplicate_ids = find_duplicate_customers(df)
    is_duplicate = df["customer_id"].isin(set(duplicate_ids))
    log.add(
        "customers", "duplicate_customers", is_duplicate.sum(), "merged into the earliest record"
    )
    df = df[~is_duplicate]
    return finish(df, "customers"), quarantine.frame(), duplicate_ids
