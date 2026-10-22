"""Cleaning for the small lookup tables: categories, suppliers and locations."""

import pandas as pd

from src.cleaning.common import drop_duplicate_keys, drop_exact_duplicates, finish
from src.cleaning.parsing import to_number
from src.cleaning.quality import Quarantine
from src.cleaning.rules import (
    UNCATEGORIZED_ID,
    UNCATEGORIZED_NAME,
    VALID_LOCATION_TYPES,
    VALID_REGIONS,
)
from src.cleaning.text import (
    clean_text,
    normalize_id,
    standardize_city,
    standardize_location_name,
    tidy_name,
)
from src.cleaning.validators import is_valid_email

DEFAULT_LEAD_TIME_DAYS = 7


def clean_categories(raw, log):
    quarantine = Quarantine("categories", log)
    df = drop_exact_duplicates(raw, "categories", log)
    df = df.assign(
        category_id=normalize_id(df["category_id"]),
        category_name=tidy_name(df["category_name"]),
    )
    df = quarantine.reject(df, df["category_id"].isna(), "missing_category_id")
    df = quarantine.reject(df, df["category_name"].isna(), "missing_category_name")
    df = drop_duplicate_keys(df, "categories", "category_id", log, quarantine)
    df = quarantine.reject(df, df.duplicated("category_name"), "duplicate_category_name")

    # products without a usable category are assigned to this one
    if UNCATEGORIZED_ID not in set(df["category_id"]):
        fallback = pd.DataFrame(
            {"category_id": [UNCATEGORIZED_ID], "category_name": [UNCATEGORIZED_NAME]}
        )
        df = pd.concat([df, fallback], ignore_index=True)
    return finish(df, "categories"), quarantine.frame()


def clean_suppliers(raw, log):
    quarantine = Quarantine("suppliers", log)
    df = drop_exact_duplicates(raw, "suppliers", log)
    df = df.assign(
        supplier_id=normalize_id(df["supplier_id"]),
        supplier_name=tidy_name(df["supplier_name"]),
        city=standardize_city(df["city"]),
        contact_email=clean_text(df["contact_email"], case="lower"),
        lead_time_days=to_number(df["lead_time_days"]),
    )
    df = quarantine.reject(df, df["supplier_id"].isna(), "missing_supplier_id")
    df = quarantine.reject(df, df["supplier_name"].isna(), "missing_supplier_name")

    bad_email = df["contact_email"].notna() & ~is_valid_email(df["contact_email"])
    log.add("suppliers", "invalid_contact_email", bad_email.sum(), "set to missing")
    df = df.assign(contact_email=df["contact_email"].mask(bad_email))

    # a missing or impossible lead time is replaced by the typical one
    bad_lead_time = ~(df["lead_time_days"] > 0)
    typical = df.loc[~bad_lead_time, "lead_time_days"].median()
    typical = DEFAULT_LEAD_TIME_DAYS if pd.isna(typical) else typical
    log.add("suppliers", "missing_lead_time", bad_lead_time.sum(), "filled with the median")
    lead_time = df["lead_time_days"].mask(bad_lead_time, typical).round().astype("int64")
    df = df.assign(lead_time_days=lead_time)

    df = drop_duplicate_keys(df, "suppliers", "supplier_id", log, quarantine)
    return finish(df, "suppliers"), quarantine.frame()


def clean_locations(raw, log):
    quarantine = Quarantine("locations", log)
    df = drop_exact_duplicates(raw, "locations", log)
    df = df.assign(
        location_id=normalize_id(df["location_id"]),
        location_name=standardize_location_name(df["location_name"]),
        city=standardize_city(df["city"]),
        state=clean_text(df["state"], case="title"),
        region=clean_text(df["region"], case="title"),
        location_type=clean_text(df["location_type"], case="title"),
    )
    df = quarantine.reject(df, df["location_id"].isna(), "missing_location_id")
    df = quarantine.reject(df, df["location_name"].isna(), "missing_location_name")
    df = quarantine.reject(df, ~df["region"].isin(VALID_REGIONS), "invalid_region")
    df = quarantine.reject(df, ~df["location_type"].isin(VALID_LOCATION_TYPES), "invalid_type")
    df = drop_duplicate_keys(df, "locations", "location_id", log, quarantine)
    return finish(df, "locations"), quarantine.frame()
