from src.cleaning.products import clean_products
from tests.helpers import raw_table

CATEGORY_IDS = ["CAT01", "CAT02"]
SUPPLIER_IDS = ["S01", "S02", "S03"]


def product(product_id, **changes):
    row = {
        "product_id": product_id,
        "product_name": f"Product {product_id}",
        "category_id": "CAT01",
        "supplier_id": "S01",
        "cost_price": "80",
        "selling_price": "100",
        "unit": "box",
    }
    return row | changes


def clean(*rows, log):
    return clean_products(raw_table("products", *rows), CATEGORY_IDS, SUPPLIER_IDS, log)


def test_prices_written_as_text_are_read(log):
    products, _ = clean(product("P1", cost_price="Rs 1,050.50", selling_price="1,299.00"), log=log)
    assert products.loc[0, "cost_price"] == 1050.5
    assert products.loc[0, "selling_price"] == 1299.0


def test_cost_above_the_selling_price_means_the_columns_were_swapped(log):
    products, _ = clean(product("P1", cost_price="150", selling_price="100"), log=log)
    assert (products.loc[0, "cost_price"], products.loc[0, "selling_price"]) == (100.0, 150.0)
    assert log.count("products", "cost_price_above_selling_price") == 1


def test_missing_cost_is_estimated_from_the_category(log):
    products, _ = clean(
        product("P1", cost_price="60", selling_price="100"),
        product("P2", cost_price="120", selling_price="200"),
        product("P3", cost_price=None, selling_price="100"),
        log=log,
    )
    assert products.set_index("product_id").loc["P3", "cost_price"] == 60.0
    assert log.count("products", "missing_cost_price") == 1


def test_uncategorized_products_do_not_set_the_cost_ratio_of_other_products(log):
    # P3 and P4 have an unknown category. Their cost ratio (10%) must not be used for P4.
    products, _ = clean(
        product("P1", cost_price="60", selling_price="100"),
        product("P2", cost_price="60", selling_price="100"),
        product("P3", category_id="BAD", supplier_id="S02", cost_price="10"),
        product("P4", category_id="BAD", supplier_id="S03", cost_price=None),
        log=log,
    )
    by_id = products.set_index("product_id")
    assert by_id.loc["P4", "category_id"] == "CAT99"
    assert by_id.loc["P4", "cost_price"] == 60.0


def test_missing_category_is_taken_from_the_supplier_only_when_it_is_unambiguous(log):
    products, _ = clean(
        product("P1", category_id="CAT01", supplier_id="S01"),
        product("P2", category_id="CAT01", supplier_id="S01"),
        product("P3", category_id=None, supplier_id="S01"),
        product("P4", category_id="CAT01", supplier_id="S02"),
        product("P5", category_id="CAT02", supplier_id="S02"),
        product("P6", category_id=None, supplier_id="S02"),
        log=log,
    )
    categories = products.set_index("product_id")["category_id"]
    assert categories["P3"] == "CAT01"  # S01 only sells beverages
    assert categories["P6"] == "CAT99"  # S02 sells two categories, so it is a guess
    assert log.count("products", "category_inferred_from_supplier") == 1
    assert log.count("products", "missing_or_unknown_category") == 1


def test_invalid_products_are_rejected_with_a_reason(log):
    products, rejected = clean(
        product("P1"),
        product("P1", product_name="Same id again"),
        product("P2", supplier_id="S99"),
        product("P3", selling_price="0"),
        product("P4", product_name=None),
        log=log,
    )
    assert products["product_id"].tolist() == ["P1"]
    assert dict(zip(rejected["product_id"], rejected["reject_reason"], strict=True)) == {
        "P2": "unknown_supplier_id",
        "P3": "invalid_selling_price",
        "P4": "missing_product_name",
        "P1": "duplicate_product_id",
    }
