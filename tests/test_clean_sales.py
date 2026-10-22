import pandas as pd

from src.cleaning.sales import (
    clean_order_items,
    clean_orders,
    drop_orders_without_items,
    finish_orders,
)
from tests.helpers import AS_OF, raw_table

CUSTOMER_IDS = ["C1", "C2"]
LOCATION_IDS = ["L01"]
PRODUCTS = pd.DataFrame({"product_id": ["P1", "P2"], "selling_price": [100.0, 50.0]})


def order(order_id, **changes):
    row = {
        "order_id": order_id,
        "customer_id": "C1",
        "location_id": "L01",
        "order_date": "2026-03-10",
        "order_status": "Completed",
        "payment_method": "UPI",
        "order_total": "1000",
    }
    return row | changes


def item(item_id, **changes):
    row = {
        "order_item_id": item_id,
        "order_id": "O1",
        "product_id": "P1",
        "quantity": "2",
        "unit_price": "100",
        "discount_pct": "10",
    }
    return row | changes


def clean_order_rows(*rows, log, customer_map=None):
    raw = raw_table("orders", *rows)
    return clean_orders(raw, CUSTOMER_IDS, LOCATION_IDS, customer_map or {}, AS_OF, log)


def clean_item_rows(*rows, log):
    return clean_order_items(raw_table("order_items", *rows), ["O1"], PRODUCTS, log)


def reasons(rejected, key):
    return dict(zip(rejected[key], rejected["reject_reason"], strict=True))


# orders


def test_order_fields_are_standardised(log):
    orders, _ = clean_order_rows(
        order(
            "o1",
            customer_id=" c1 ",
            location_id="l01",
            order_date="10/03/2026",
            order_status="COMPLETE",
            payment_method="cc",
            order_total="Rs 1,000",
        ),
        log=log,
    )
    row = orders.iloc[0]
    assert (row["order_id"], row["customer_id"], row["location_id"]) == ("O1", "C1", "L01")
    assert row["order_date"] == pd.Timestamp("2026-03-10")
    assert row["order_status"] == "Completed"
    assert row["payment_method"] == "Credit Card"
    assert row["raw_order_total"] == 1000.0


def test_orders_of_a_merged_customer_move_to_the_customer_that_was_kept(log):
    orders, _ = clean_order_rows(order("O1", customer_id="C2"), customer_map={"C2": "C1"}, log=log)
    assert orders.loc[0, "customer_id"] == "C1"
    assert log.count("orders", "customer_id_of_duplicate_customer") == 1


def test_invalid_orders_are_rejected_with_a_reason(log):
    orders, rejected = clean_order_rows(
        order("O1"),
        order("O2", order_date="2026-10-16"),
        order("O3", order_date="2019-12-31"),
        order("O4", order_date="30/02/2026"),
        order("O5", customer_id="C99"),
        order("O6", customer_id=None),
        order("O7", location_id="L99"),
        order("O8", order_status="pending"),
        order("O1", order_date="2026-03-11"),
        log=log,
    )
    assert orders["order_id"].tolist() == ["O1"]
    assert reasons(rejected, "order_id") == {
        "O2": "order_date_out_of_range",
        "O3": "order_date_out_of_range",
        "O4": "invalid_order_date",
        "O5": "unknown_customer_id",
        "O6": "missing_customer_id",
        "O7": "unknown_location_id",
        "O8": "unknown_order_status",
        "O1": "duplicate_order_id",
    }


def test_missing_payment_method_becomes_unknown(log):
    orders, _ = clean_order_rows(order("O1", payment_method=None), log=log)
    assert orders.loc[0, "payment_method"] == "Unknown"


# order items


def test_negative_quantity_is_a_sign_error_and_is_flipped(log):
    items, _ = clean_item_rows(item("OI1", quantity="-3"), log=log)
    assert items.loc[0, "quantity"] == 3
    assert log.count("order_items", "negative_quantity") == 1


def test_quantity_written_as_decimal_text_is_accepted(log):
    items, _ = clean_item_rows(item("OI1", quantity="12.0"), log=log)
    assert items.loc[0, "quantity"] == 12


def test_quantities_that_cannot_be_right_are_rejected(log):
    items, rejected = clean_item_rows(
        item("OI1"),
        item("OI2", quantity="0"),
        item("OI3", quantity="501"),
        item("OI4", quantity=None),
        item("OI5", quantity="2.5"),
        log=log,
    )
    assert items["order_item_id"].tolist() == ["OI1"]
    assert reasons(rejected, "order_item_id") == {
        "OI2": "zero_quantity",
        "OI3": "quantity_outlier",
        "OI4": "missing_quantity",
        "OI5": "non_integer_quantity",
    }


def test_missing_and_outlier_prices_fall_back_to_the_list_price(log):
    items, _ = clean_item_rows(
        item("OI1", unit_price=None),
        item("OI2", unit_price="1000"),
        item("OI3", unit_price="95"),
        item("OI4", unit_price="Rs 105.50"),
        log=log,
    )
    prices = items.set_index("order_item_id")["unit_price"].to_dict()
    assert prices == {"OI1": 100.0, "OI2": 100.0, "OI3": 95.0, "OI4": 105.5}


def test_missing_or_invalid_discount_becomes_zero(log):
    items, _ = clean_item_rows(
        item("OI1", discount_pct=None),
        item("OI2", discount_pct="150"),
        item("OI3", discount_pct="7.5%"),
        log=log,
    )
    discounts = items.set_index("order_item_id")["discount_pct"].to_dict()
    assert discounts == {"OI1": 0.0, "OI2": 0.0, "OI3": 7.5}


def test_lines_of_missing_orders_and_unknown_products_are_rejected(log):
    items, rejected = clean_item_rows(
        item("OI1"),
        item("OI2", order_id="O9"),
        item("OI3", product_id="P99"),
        log=log,
    )
    assert items["order_item_id"].tolist() == ["OI1"]
    assert reasons(rejected, "order_item_id") == {
        "OI2": "order_not_found",
        "OI3": "unknown_product_id",
    }


def test_duplicate_lines_are_dropped_once(log):
    items, _ = clean_item_rows(item("OI1"), item("OI1"), log=log)
    assert len(items) == 1
    assert log.count("order_items", "exact_duplicate_rows") == 1


# order level checks


def test_an_order_without_valid_lines_is_dropped(log):
    orders = pd.DataFrame({"order_id": ["O1", "O2"]})
    items = pd.DataFrame({"order_id": ["O1"]})
    kept, rejected = drop_orders_without_items(orders, items, log)
    assert kept["order_id"].tolist() == ["O1"]
    assert rejected["reject_reason"].tolist() == ["order_without_valid_items"]


def test_order_total_in_the_raw_file_is_only_a_cross_check(log):
    orders = pd.DataFrame(
        {
            "order_id": ["O1", "O2", "O3"],
            "customer_id": "C1",
            "location_id": "L01",
            "order_date": pd.Timestamp("2026-03-10"),
            "order_status": "Completed",
            "payment_method": "UPI",
            "raw_order_total": [180.0, 999.0, None],
        }
    )
    items = pd.DataFrame(
        {
            "order_id": ["O1", "O2", "O3"],
            "quantity": [2, 1, 1],
            "unit_price": [100.0, 100.0, 50.0],
            "discount_pct": [10.0, 0.0, 0.0],
        }
    )
    result = finish_orders(orders, items, log)
    assert "raw_order_total" not in result.columns
    assert log.count("orders", "order_total_differs_from_lines") == 1
    assert log.count("orders", "missing_order_total") == 1
