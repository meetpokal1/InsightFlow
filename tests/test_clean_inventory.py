import pandas as pd

from src.cleaning.inventory import clean_inventory
from tests.helpers import raw_table

PRODUCTS = pd.DataFrame(
    {"product_id": ["P1", "P2", "P3"], "category_id": ["CAT01", "CAT01", "CAT02"]}
)
LOCATION_IDS = ["L01", "L02"]


def stock(inventory_id, **changes):
    row = {
        "inventory_id": inventory_id,
        "product_id": "P1",
        "location_id": "L01",
        "quantity_on_hand": "50",
        "reorder_level": "20",
        "last_restocked_date": "2026-09-01",
        "snapshot_date": "2026-09-30",
    }
    return row | changes


def clean(*rows, log):
    return clean_inventory(raw_table("inventory", *rows), PRODUCTS, LOCATION_IDS, log)


def test_negative_stock_counts_as_an_empty_shelf(log):
    inventory, _ = clean(stock("INV1", quantity_on_hand="-8"), log=log)
    assert inventory.loc[0, "quantity_on_hand"] == 0
    assert log.count("inventory", "negative_quantity_on_hand") == 1


def test_quantity_written_with_a_unit_is_read(log):
    inventory, _ = clean(stock("INV1", quantity_on_hand="120 units"), log=log)
    assert inventory.loc[0, "quantity_on_hand"] == 120


def test_restock_date_after_the_snapshot_is_removed(log):
    inventory, _ = clean(stock("INV1", last_restocked_date="2026-10-05"), log=log)
    assert pd.isna(inventory.loc[0, "last_restocked_date"])
    assert log.count("inventory", "restock_date_after_snapshot") == 1


def test_missing_reorder_level_gets_the_median_of_the_category(log):
    inventory, _ = clean(
        stock("INV1", product_id="P1", reorder_level="20"),
        stock("INV2", product_id="P1", location_id="L02", reorder_level="40"),
        stock("INV3", product_id="P2", reorder_level=None),
        stock("INV4", product_id="P3", reorder_level="500"),
        log=log,
    )
    assert inventory.set_index("inventory_id").loc["INV3", "reorder_level"] == 30


def test_two_rows_for_the_same_product_and_location_keep_the_latest_restock(log):
    inventory, rejected = clean(
        stock("INV1", quantity_on_hand="10", last_restocked_date="2026-07-01"),
        stock("INV2", quantity_on_hand="99", last_restocked_date="2026-09-15"),
        log=log,
    )
    assert inventory["inventory_id"].tolist() == ["INV2"]
    assert rejected["reject_reason"].tolist() == ["stale_duplicate_stock_row"]


def test_rows_for_unknown_products_or_locations_are_rejected(log):
    inventory, rejected = clean(
        stock("INV1"),
        stock("INV2", product_id="P99"),
        stock("INV3", location_id="L99"),
        log=log,
    )
    assert inventory["inventory_id"].tolist() == ["INV1"]
    assert dict(zip(rejected["inventory_id"], rejected["reject_reason"], strict=True)) == {
        "INV2": "unknown_product_id",
        "INV3": "unknown_location_id",
    }
