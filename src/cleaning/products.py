"""Cleaning for the products table."""

from src.cleaning.common import drop_exact_duplicates, finish
from src.cleaning.parsing import to_number
from src.cleaning.quality import Quarantine
from src.cleaning.rules import DEFAULT_COST_RATIO, UNCATEGORIZED_ID
from src.cleaning.text import clean_text, normalize_id


def clean_products(raw, category_ids, supplier_ids, log):
    quarantine = Quarantine("products", log)
    df = drop_exact_duplicates(raw, "products", log)
    df = df.assign(
        product_id=normalize_id(df["product_id"]),
        product_name=clean_text(df["product_name"]),
        category_id=normalize_id(df["category_id"]),
        supplier_id=normalize_id(df["supplier_id"]),
        cost_price=to_number(df["cost_price"]),
        selling_price=to_number(df["selling_price"]),
        unit=clean_text(df["unit"], case="lower"),
    )
    df = quarantine.reject(df, df["product_id"].isna(), "missing_product_id")
    df = quarantine.reject(df, df["product_name"].isna(), "missing_product_name")
    df = quarantine.reject(df, df.duplicated("product_id"), "duplicate_product_id")
    df = quarantine.reject(df, ~(df["selling_price"] > 0), "invalid_selling_price")
    df = quarantine.reject(df, df["cost_price"] < 0, "negative_cost_price")
    df = quarantine.reject(df, ~df["supplier_id"].isin(set(supplier_ids)), "unknown_supplier_id")

    # A missing category is read from the supplier when all of that supplier's other
    # products share one category. Anything still unknown goes to Uncategorized.
    no_category = ~df["category_id"].isin(set(category_ids))
    known = df[~no_category].groupby("supplier_id")["category_id"].agg(["first", "nunique"])
    only_category = known.loc[known["nunique"] == 1, "first"]
    from_supplier = df["supplier_id"].map(only_category)
    inferred = no_category & from_supplier.notna()
    log.add("products", "category_inferred_from_supplier", inferred.sum(), "used supplier category")
    log.add(
        "products", "missing_or_unknown_category", (no_category & ~inferred).sum(), "Uncategorized"
    )
    category_id = df["category_id"].mask(no_category, from_supplier).fillna(UNCATEGORIZED_ID)
    df = df.assign(category_id=category_id)

    # a cost above the price means the two columns were swapped when the row was typed in
    swapped = df["cost_price"] > df["selling_price"]
    log.add("products", "cost_price_above_selling_price", swapped.sum(), "swapped the two prices")
    df = df.assign(
        cost_price=df["cost_price"].mask(swapped, df["selling_price"]),
        selling_price=df["selling_price"].mask(swapped, df["cost_price"]),
    )

    # a missing cost is estimated from the usual cost-to-price ratio of the category
    # Uncategorized is not a real group of similar products, so it is left out of the medians
    cost_ratio = df["cost_price"] / df["selling_price"]
    peer_ratio = cost_ratio.where(df["category_id"] != UNCATEGORIZED_ID)
    category_ratio = peer_ratio.groupby(df["category_id"]).transform("median")
    fallback_ratio = category_ratio.fillna(peer_ratio.median()).fillna(DEFAULT_COST_RATIO)
    missing_cost = df["cost_price"].isna()
    log.add("products", "missing_cost_price", missing_cost.sum(), "estimated from category ratio")
    estimated_cost = (df["selling_price"] * fallback_ratio).round(2)
    df = df.assign(
        cost_price=df["cost_price"].fillna(estimated_cost).round(2),
        selling_price=df["selling_price"].round(2),
    )
    return finish(df, "products"), quarantine.frame()
