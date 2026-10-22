"""Cleaning for the inventory snapshot."""

from src.cleaning.common import drop_exact_duplicates, finish
from src.cleaning.parsing import parse_dates, to_number
from src.cleaning.quality import Quarantine
from src.cleaning.text import clean_text, normalize_id


def clean_inventory(raw, products, location_ids, log):
    quarantine = Quarantine("inventory", log)
    df = drop_exact_duplicates(raw, "inventory", log)

    restocked_text = clean_text(df["last_restocked_date"])
    restocked = parse_dates(restocked_text)
    invalid_date = restocked_text.notna() & restocked.isna()
    log.add("inventory", "invalid_last_restocked_date", invalid_date.sum(), "set to missing")

    df = df.assign(
        inventory_id=normalize_id(df["inventory_id"]),
        product_id=normalize_id(df["product_id"]),
        location_id=normalize_id(df["location_id"]),
        quantity_on_hand=to_number(df["quantity_on_hand"]),
        reorder_level=to_number(df["reorder_level"]),
        last_restocked_date=restocked,
        snapshot_date=parse_dates(df["snapshot_date"]),
    )
    df = quarantine.reject(df, df["inventory_id"].isna(), "missing_inventory_id")
    df = quarantine.reject(df, df.duplicated("inventory_id"), "duplicate_inventory_id")
    known_products = set(products["product_id"])
    df = quarantine.reject(df, ~df["product_id"].isin(known_products), "unknown_product_id")
    df = quarantine.reject(df, ~df["location_id"].isin(set(location_ids)), "unknown_location_id")
    df = quarantine.reject(df, df["quantity_on_hand"].isna(), "missing_quantity_on_hand")
    df = quarantine.reject(df, df["snapshot_date"].isna(), "missing_snapshot_date")

    # a negative stock level is a system or typing error, so it counts as an empty shelf
    negative = df["quantity_on_hand"] < 0
    log.add("inventory", "negative_quantity_on_hand", negative.sum(), "set to 0")
    df = df.assign(quantity_on_hand=df["quantity_on_hand"].clip(lower=0))

    restocked_after_snapshot = df["last_restocked_date"] > df["snapshot_date"]
    log.add(
        "inventory", "restock_date_after_snapshot", restocked_after_snapshot.sum(), "set to missing"
    )
    df = df.assign(last_restocked_date=df["last_restocked_date"].mask(restocked_after_snapshot))

    # a missing reorder level gets the median of the same category
    category = df["product_id"].map(products.set_index("product_id")["category_id"])
    category_median = df["reorder_level"].groupby(category).transform("median")
    fallback = category_median.fillna(df["reorder_level"].median()).fillna(0).round()
    no_reorder_level = ~(df["reorder_level"] >= 0)
    log.add(
        "inventory", "missing_reorder_level", no_reorder_level.sum(), "filled with category median"
    )
    df = df.assign(reorder_level=df["reorder_level"].mask(no_reorder_level, fallback))

    # two rows for the same product and location: keep the most recently restocked one
    newest_first = df.sort_values("last_restocked_date", ascending=False, na_position="last")
    key = ["product_id", "location_id", "snapshot_date"]
    stale = newest_first.duplicated(subset=key, keep="first").reindex(df.index)
    df = quarantine.reject(df, stale, "stale_duplicate_stock_row")

    df = df.assign(
        quantity_on_hand=df["quantity_on_hand"].astype("int64"),
        reorder_level=df["reorder_level"].astype("int64"),
    )
    return finish(df, "inventory"), quarantine.frame()
