"""Unit tests for the Power BI Project (PBIP) deliverable structure, semantic model, and measures."""

import json
import pathlib

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
POWERBI_DIR = PROJECT_ROOT / "powerbi"


def test_pbip_project_files_exist():
    """Verify modern PBIP directory structure and entry points exist."""
    assert (POWERBI_DIR / "InsightFlow.pbip").exists()
    assert (POWERBI_DIR / "InsightFlow.Report" / "definition.pbir").exists()
    assert (POWERBI_DIR / "InsightFlow.Report" / "report.json").exists() or (
        POWERBI_DIR / "InsightFlow.Report" / "definition" / "pages" / "pages.json"
    ).exists()
    assert (POWERBI_DIR / "InsightFlow.SemanticModel" / "definition.pbism").exists()
    assert (POWERBI_DIR / "InsightFlow.SemanticModel" / "model.bim").exists()


def test_pbip_shortcut_schema_and_path_resolution():
    """Verify InsightFlow.pbip conforms strictly to Microsoft PBIP 1.0 schema.

    Guards against desktop parser errors like 'Property enableAutoAuth has not been defined'.
    """
    pbip_file = POWERBI_DIR / "InsightFlow.pbip"
    with open(pbip_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Version must be "1.0"
    assert data.get("version") == "1.0"

    # 2. Check artifacts
    artifacts = data.get("artifacts")
    assert isinstance(artifacts, list) and len(artifacts) >= 1
    report_entry = artifacts[0].get("report", {})
    report_rel_path = report_entry.get("path")
    assert report_rel_path == "InsightFlow.Report"
    assert (POWERBI_DIR / report_rel_path).is_dir()

    # 3. Settings schema compliance: enableAutoAuth is rejected by Power BI Desktop
    settings = data.get("settings")
    if settings is not None:
        assert isinstance(settings, dict)
        assert "enableAutoAuth" not in settings
        # The only valid schema property for settings is enableAutoRecovery
        allowed_setting_keys = {"enableAutoRecovery"}
        assert set(settings.keys()).issubset(allowed_setting_keys)

    # 4. Check definition.pbir relative model resolution
    pbir_file = POWERBI_DIR / "InsightFlow.Report" / "definition.pbir"
    with open(pbir_file, "r", encoding="utf-8") as f:
        pbir_data = json.load(f)

    model_path = pbir_data.get("datasetReference", {}).get("byPath", {}).get("path")
    assert model_path == "../InsightFlow.SemanticModel"
    resolved_model_dir = (pbir_file.parent / model_path).resolve()
    assert resolved_model_dir.is_dir()
    assert (resolved_model_dir / "definition.pbism").exists()
    assert (resolved_model_dir / "model.bim").exists()


def test_report_pages_configuration():
    """Verify all 4 required report pages are defined in PBIR definition or report.json."""
    pages_json_file = POWERBI_DIR / "InsightFlow.Report" / "definition" / "pages" / "pages.json"
    report_file = POWERBI_DIR / "InsightFlow.Report" / "report.json"

    expected_pages = [
        "Executive Profitability",
        "Margin Investigation",
        "Inventory Decisions",
        "Data Integrity & Pipeline Assurance",
    ]

    if pages_json_file.exists():
        with open(pages_json_file, "r", encoding="utf-8") as f:
            pages_data = json.load(f)
        page_names = []
        for p_folder in pages_data.get("pageOrder", []):
            page_meta_file = pages_json_file.parent / p_folder / "page.json"
            if page_meta_file.exists():
                with open(page_meta_file, "r", encoding="utf-8") as pf:
                    page_meta = json.load(pf)
                    page_names.append(page_meta.get("displayName"))
        assert page_names == expected_pages
    elif report_file.exists():
        with open(report_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        sections = data.get("sections", [])
        page_names = [s.get("displayName") for s in sections]
        assert page_names == expected_pages
    else:
        pytest.fail(
            "Neither definition/pages/pages.json nor report.json found in InsightFlow.Report"
        )


def test_semantic_model_star_schema_and_measures():
    """Verify semantic model defines star schema tables, relationships, and key DAX measures."""
    model_file = POWERBI_DIR / "InsightFlow.SemanticModel" / "model.bim"
    with open(model_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    model = data.get("model", {})
    tables = {t["name"]: t for t in model.get("tables", [])}

    # Verify tables
    expected_tables = {
        "Sales",
        "Inventory",
        "Product",
        "Customer",
        "Location",
        "Date",
        "DataQualityReconciliation",
    }
    assert expected_tables.issubset(tables.keys())

    # Verify relationships
    rel_names = {r["name"] for r in model.get("relationships", [])}
    expected_rels = {
        "Sales_Product",
        "Sales_Customer",
        "Sales_Location",
        "Sales_Date",
        "Inventory_Product",
        "Inventory_Location",
    }
    assert expected_rels.issubset(rel_names)

    # Verify DAX measures in Sales
    sales_measures = {m["name"]: m["expression"] for m in tables["Sales"].get("measures", [])}
    assert "Revenue" in sales_measures
    assert "Gross Profit" in sales_measures
    assert "Gross Margin %" in sales_measures
    assert "Basmati Rice Net Revenue" in sales_measures
    assert "Basmati Break Even Volume Decline %" in sales_measures

    # Verify DAX measures in Inventory
    inv_measures = {m["name"]: m["expression"] for m in tables["Inventory"].get("measures", [])}
    assert "Stock Value" in inv_measures
    assert "Replenishment Qty Required" in inv_measures
    assert "Replenishment Cost Estimate" in inv_measures
    assert "Stock Gap Retail Valuation" in inv_measures
    assert "Stockout Positions" in inv_measures


def test_inventory_currency_cards_use_display_only_measures():
    """Keep currency measures numeric while card-specific measures render INR lakh/crore labels."""
    model_file = POWERBI_DIR / "InsightFlow.SemanticModel" / "model.bim"
    with open(model_file, "r", encoding="utf-8") as f:
        model_data = json.load(f)

    tables = {table["name"]: table for table in model_data["model"]["tables"]}
    inv_measures = {measure["name"]: measure for measure in tables["Inventory"].get("measures", [])}

    # Canonical measures must remain numeric so ratios, totals and future analysis are valid.
    expected_numeric = {
        "Stock Value": "SUM(Inventory[inventory_value])",
        "Replenishment Cost Estimate": "SUM(Inventory[replenishment_cost_estimate])",
        "Stock Gap Retail Valuation": "SUM(Inventory[stock_gap_retail_valuation])",
    }
    for name, expression in expected_numeric.items():
        assert inv_measures[name]["expression"] == expression, (
            f"Inventory.{name} must remain a numeric aggregation"
        )

    # Human-readable rupee units belong in separate text-only card measures.
    expected_display = {
        "Stock Value Display": 'FORMAT(DIVIDE([Stock Value], 10000000), "0.00")',
        "Replenishment Cost Estimate Display": (
            'FORMAT(DIVIDE([Replenishment Cost Estimate], 100000), "0.00")'
        ),
        "Stock Gap Retail Valuation Display": (
            'FORMAT(DIVIDE([Stock Gap Retail Valuation], 100000), "0.00")'
        ),
    }
    for name, fragment in expected_display.items():
        assert name in inv_measures, f"Missing card display measure: {name}"
        assert fragment in inv_measures[name]["expression"]

    tmdl_file = (
        POWERBI_DIR / "InsightFlow.SemanticModel" / "definition" / "tables" / "Inventory.tmdl"
    )
    tmdl = tmdl_file.read_text(encoding="utf-8")
    for name, expression in expected_numeric.items():
        assert f"measure '{name}' = {expression}" in tmdl
    for name in expected_display:
        assert f"measure '{name}' =" in tmdl

    # Each rupee card must query its display-only measure, never the numeric amount.
    card_bindings = {
        "CardStockVal": "Stock Value Display",
        "CardReplenishCost": "Replenishment Cost Estimate Display",
        "CardStockGapRetail": "Stock Gap Retail Valuation Display",
    }
    pages_dir = POWERBI_DIR / "InsightFlow.Report" / "definition" / "pages"
    for visual_name, measure_name in card_bindings.items():
        visual_file = next(pages_dir.glob(f"*/visuals/{visual_name}/visual.json"))
        with open(visual_file, "r", encoding="utf-8") as f:
            visual_data = json.load(f)
        projections = visual_data["visual"]["query"]["queryState"]["Data"]["projections"]
        assert len(projections) == 1
        assert projections[0]["field"]["Measure"]["Property"] == measure_name
        assert projections[0]["queryRef"] == f"Inventory.{measure_name}"


def test_powerbi_data_csvs_exist_and_non_empty():
    """Verify that powerbi/data contains all required CSVs for local desktop loading."""
    data_dir = POWERBI_DIR / "data"
    required_csvs = [
        "vw_fact_sales.csv",
        "vw_fact_inventory.csv",
        "vw_dim_product.csv",
        "vw_dim_customer.csv",
        "vw_dim_location.csv",
        "dim_date.csv",
        "data_assurance_reconciliation.csv",
    ]
    for csv_name in required_csvs:
        f = data_dir / csv_name
        assert f.exists()
        assert f.stat().st_size > 50


def test_pbip_data_folder_parameter_and_source_paths():
    """Verify DataFolder parameter exists and all 7 tables resolve to valid CSV paths on disk."""
    import re

    model_file = POWERBI_DIR / "InsightFlow.SemanticModel" / "model.bim"
    with open(model_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    model = data.get("model", {})
    expressions = {e["name"]: e for e in model.get("expressions", [])}
    assert "DataFolder" in expressions, "DataFolder parameter missing from model expressions"

    # Verify DataFolder parameter expression metadata
    df_expr = expressions["DataFolder"].get("expression", [])
    df_str = "\n".join(df_expr) if isinstance(df_expr, list) else df_expr
    assert "IsParameterQuery=true" in df_str or "IsParameterQuery = true" in df_str

    # Extract the configured path and validate parameter definition
    match = re.search(r'"([^"]+)"\s*meta', df_str)
    assert match, f"Could not extract folder path from: {df_str}"
    raw_path = match.group(1)
    assert len(raw_path.strip()) > 0, "Configured DataFolder path string is empty"

    # Verify every table uses DataFolder and its target CSV exists and is non-empty
    expected_csvs = {
        "Sales": "vw_fact_sales.csv",
        "Inventory": "vw_fact_inventory.csv",
        "Product": "vw_dim_product.csv",
        "Customer": "vw_dim_customer.csv",
        "Location": "vw_dim_location.csv",
        "Date": "dim_date.csv",
        "DataQualityReconciliation": "data_assurance_reconciliation.csv",
    }

    project_data_dir = POWERBI_DIR / "data"
    configured_folder = pathlib.Path(raw_path)

    tables = {t["name"]: t for t in model.get("tables", [])}
    for table_name, csv_filename in expected_csvs.items():
        assert table_name in tables, f"Table {table_name} missing from model"
        partitions = tables[table_name].get("partitions", [])
        assert len(partitions) >= 1, f"Table {table_name} has no partitions"
        source_expr = partitions[0].get("source", {}).get("expression", "")
        expr_str = "\n".join(source_expr) if isinstance(source_expr, list) else source_expr

        # Must NOT use unparameterized relative paths
        assert 'File.Contents("data/' not in expr_str, (
            f"Table {table_name} contains unparameterized relative path"
        )
        assert 'File.Contents("./' not in expr_str, (
            f"Table {table_name} contains unparameterized relative path"
        )

        # Must reference DataFolder parameter
        assert "DataFolder" in expr_str, (
            f"Table {table_name} does not reference DataFolder parameter"
        )
        assert csv_filename in expr_str, f"Table {table_name} does not reference {csv_filename}"

        # Validate that the generated CSV exists in project powerbi/data/
        project_csv_file = project_data_dir / csv_filename
        assert project_csv_file.is_file(), (
            f"Target CSV does not exist in powerbi/data: {project_csv_file}"
        )
        assert project_csv_file.stat().st_size > 0, (
            f"Target CSV in powerbi/data is empty: {project_csv_file}"
        )

        # If running on the workstation where the configured folder exists, verify it matches
        if configured_folder.is_dir():
            configured_csv_file = configured_folder / csv_filename
            assert configured_csv_file.is_file(), (
                f"Target CSV does not exist in configured folder: {configured_csv_file}"
            )
            assert configured_csv_file.stat().st_size > 0, (
                f"Target CSV in configured folder is empty: {configured_csv_file}"
            )


def test_pbir_visual_containers_bindings_and_data_roles():
    """Verify all PBIR visual.json containers have valid queryState bindings and model references."""
    pages_dir = POWERBI_DIR / "InsightFlow.Report" / "definition" / "pages"
    if not pages_dir.exists():
        pytest.skip("PBIR pages directory not present")

    visual_files = list(pages_dir.glob("*/visuals/*/visual.json"))
    assert len(visual_files) >= 25, (
        f"Expected at least 25 visual containers, found {len(visual_files)}"
    )

    model_file = POWERBI_DIR / "InsightFlow.SemanticModel" / "model.bim"
    with open(model_file, "r", encoding="utf-8") as f:
        bim_data = json.load(f)
    tables = {t["name"]: t for t in bim_data.get("model", {}).get("tables", [])}

    for vf in visual_files:
        with open(vf, "r", encoding="utf-8") as f:
            v_data = json.load(f)
        v_type = v_data.get("visual", {}).get("visualType")
        v_name = v_data.get("name")

        if v_type == "textbox":
            paragraphs = (
                v_data.get("visual", {})
                .get("objects", {})
                .get("general", [{}])[0]
                .get("properties", {})
                .get("paragraphs", [])
            )
            assert len(paragraphs) > 0, f"Textbox {v_name} has no paragraphs"
            val = paragraphs[0].get("textRuns", [{}])[0].get("value", "")
            assert len(val) > 0, f"Textbox {v_name} has empty text value"
        else:
            query_state = v_data.get("visual", {}).get("query", {}).get("queryState", {})
            assert len(query_state) > 0, f"Visual {v_name} ({v_type}) has empty queryState"

            total_proj = 0
            for _role, role_dict in query_state.items():
                projections = role_dict.get("projections", [])
                total_proj += len(projections)
                for proj in projections:
                    field = proj.get("field", {})
                    if "Measure" in field:
                        entity = field["Measure"]["Expression"]["SourceRef"]["Entity"]
                        prop = field["Measure"]["Property"]
                        assert entity in tables, f"Visual {v_name}: Entity '{entity}' not in model"
                        measure_names = {m["name"] for m in tables[entity].get("measures", [])}
                        assert prop in measure_names, (
                            f"Visual {v_name}: Measure '{prop}' not in table '{entity}'"
                        )
                    elif "Column" in field:
                        entity = field["Column"]["Expression"]["SourceRef"]["Entity"]
                        prop = field["Column"]["Property"]
                        assert entity in tables, f"Visual {v_name}: Entity '{entity}' not in model"
                        col_names = {c["name"] for c in tables[entity].get("columns", [])}
                        assert prop in col_names, (
                            f"Visual {v_name}: Column '{prop}' not in table '{entity}'"
                        )
                    else:
                        pytest.fail(f"Visual {v_name}: Unknown field projection format: {field}")
            assert total_proj > 0, f"Visual {v_name} ({v_type}) has 0 projections"


def test_customer_date_columns_and_powerquery_handling():
    """Verify Customer date columns handling, ISO validation, null conversion, and model types.

    Guards against VertiPaq model loading failure:
    'Datatype conversion failed for [Table: '', Column: '', Value: '']. (Customer (19); first order date (86))'
    """
    import csv
    import datetime

    customer_csv = POWERBI_DIR / "data" / "vw_dim_customer.csv"
    assert customer_csv.exists(), "vw_dim_customer.csv not found"

    # 1. Verify row count and column presence
    with open(customer_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 800, f"Expected 800 customers, found {len(rows)}"
    expected_fields = {
        "customer_id",
        "customer_name",
        "city",
        "customer_type",
        "signup_date",
        "first_order_date",
        "last_order_date",
        "segment",
    }
    assert expected_fields.issubset(rows[0].keys())

    # 2. Verify date value distributions and format adherence
    blank_signup = 0
    blank_first_order = 0
    blank_last_order = 0

    for r in rows:
        # signup_date
        s_date = r["signup_date"].strip()
        if not s_date:
            blank_signup += 1
        else:
            datetime.date.fromisoformat(s_date)

        # first_order_date
        fo_date = r["first_order_date"].strip()
        if not fo_date:
            blank_first_order += 1
        else:
            datetime.date.fromisoformat(fo_date)

        # last_order_date
        lo_date = r["last_order_date"].strip()
        if not lo_date:
            blank_last_order += 1
        else:
            datetime.date.fromisoformat(lo_date)

    # Exactly 17 unrecorded signup dates and 20 no-purchase customers
    assert blank_signup == 17, f"Expected 17 blank signup dates, found {blank_signup}"
    assert blank_first_order == 20, (
        f"Expected 20 blank first_order dates, found {blank_first_order}"
    )
    assert blank_last_order == 20, f"Expected 20 blank last_order dates, found {blank_last_order}"

    # 3. Verify semantic model column types and formatString in model.bim
    model_file = POWERBI_DIR / "InsightFlow.SemanticModel" / "model.bim"
    with open(model_file, "r", encoding="utf-8") as f:
        bim_data = json.load(f)

    tables = {t["name"]: t for t in bim_data.get("model", {}).get("tables", [])}
    assert "Customer" in tables, "Customer table missing from model.bim"
    customer_cols = {c["name"]: c for c in tables["Customer"].get("columns", [])}

    for col_name in ["signup_date", "first_order_date", "last_order_date"]:
        assert col_name in customer_cols, f"Column {col_name} missing from Customer table"
        assert customer_cols[col_name].get("dataType") == "dateTime", (
            f"Customer.{col_name} dataType must be dateTime, got {customer_cols[col_name].get('dataType')}"
        )
        assert customer_cols[col_name].get("formatString") == "yyyy-mm-dd", (
            f"Customer.{col_name} formatString must be yyyy-mm-dd, got {customer_cols[col_name].get('formatString')}"
        )

    # 4. Verify Power Query M partition replaces blanks with null and applies TransformColumnTypes
    cust_partitions = tables["Customer"].get("partitions", [])
    assert len(cust_partitions) >= 1, "Customer table has no partitions"
    cust_expr = cust_partitions[0].get("source", {}).get("expression", [])
    cust_expr_str = "\n".join(cust_expr) if isinstance(cust_expr, list) else cust_expr

    assert "ReplaceValue" in cust_expr_str, (
        "Customer partition missing Table.ReplaceValue for blanks"
    )
    assert "TransformColumnTypes" in cust_expr_str, (
        "Customer partition missing Table.TransformColumnTypes"
    )
    assert (
        '"signup_date", type date' in cust_expr_str or '{"signup_date", type date}' in cust_expr_str
    )
    assert (
        '"first_order_date", type date' in cust_expr_str
        or '{"first_order_date", type date}' in cust_expr_str
    )
    assert (
        '"last_order_date", type date' in cust_expr_str
        or '{"last_order_date", type date}' in cust_expr_str
    )


def test_inventory_date_columns_and_powerquery_handling():
    """Verify Inventory date and numeric blank handling and semantic model alignment."""
    import csv
    import datetime

    inv_csv = POWERBI_DIR / "data" / "vw_fact_inventory.csv"
    assert inv_csv.exists(), "vw_fact_inventory.csv not found"

    with open(inv_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 449, f"Expected 449 inventory positions, found {len(rows)}"

    blank_restock = 0
    for r in rows:
        snapshot = r["snapshot_date"].strip()
        assert snapshot, "snapshot_date cannot be empty"
        datetime.date.fromisoformat(snapshot)

        restock = r["last_restocked_date"].strip()
        if not restock:
            blank_restock += 1
        else:
            datetime.date.fromisoformat(restock)

    assert blank_restock == 5, f"Expected 5 blank last_restocked_date values, found {blank_restock}"

    model_file = POWERBI_DIR / "InsightFlow.SemanticModel" / "model.bim"
    with open(model_file, "r", encoding="utf-8") as f:
        bim_data = json.load(f)

    tables = {t["name"]: t for t in bim_data.get("model", {}).get("tables", [])}
    assert "Inventory" in tables, "Inventory table missing from model.bim"
    inv_cols = {c["name"]: c for c in tables["Inventory"].get("columns", [])}

    for col_name in ["snapshot_date", "last_restocked_date"]:
        assert col_name in inv_cols, f"Column {col_name} missing from Inventory table"
        assert inv_cols[col_name].get("dataType") == "dateTime", (
            f"Inventory.{col_name} dataType must be dateTime, got {inv_cols[col_name].get('dataType')}"
        )

    inv_partitions = tables["Inventory"].get("partitions", [])
    assert len(inv_partitions) >= 1, "Inventory table has no partitions"
    inv_expr = inv_partitions[0].get("source", {}).get("expression", [])
    inv_expr_str = "\n".join(inv_expr) if isinstance(inv_expr, list) else inv_expr

    assert "ReplaceValue" in inv_expr_str, "Inventory partition missing Table.ReplaceValue"
    assert "last_restocked_date" in inv_expr_str
    assert "TransformColumnTypes" in inv_expr_str
    assert (
        '"snapshot_date", type date' in inv_expr_str
        or '{"snapshot_date", type date}' in inv_expr_str
    )
    assert (
        '"last_restocked_date", type date' in inv_expr_str
        or '{"last_restocked_date", type date}' in inv_expr_str
    )


def test_report_json_visual_containers_and_prototype_queries():
    """Verify standard report.json has all 4 pages and valid prototypeQuery bindings for every visual."""
    report_file = POWERBI_DIR / "InsightFlow.Report" / "report.json"
    assert report_file.exists(), "InsightFlow.Report/report.json not found"

    with open(report_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    sections = data.get("sections", [])
    assert len(sections) == 4, f"Expected 4 sections in report.json, found {len(sections)}"

    expected_page_titles = [
        "Executive Profitability",
        "Margin Investigation",
        "Inventory Decisions",
        "Data Integrity & Pipeline Assurance",
    ]
    actual_page_titles = [s.get("displayName") for s in sections]
    assert actual_page_titles == expected_page_titles

    total_visuals = 0
    for section in sections:
        vcs = section.get("visualContainers", [])
        assert len(vcs) >= 5, f"Section {section.get('displayName')} has fewer than 5 visuals"
        total_visuals += len(vcs)

        for vc in vcs:
            cfg = json.loads(vc.get("config", "{}"))
            sv = cfg.get("singleVisual", {})
            v_type = sv.get("visualType")
            v_name = cfg.get("name")

            if v_type == "textbox":
                paragraphs = (
                    sv.get("objects", {})
                    .get("general", [{}])[0]
                    .get("properties", {})
                    .get("paragraphs", [])
                )
                assert len(paragraphs) > 0, f"Textbox {v_name} has no paragraphs"
            else:
                projections = sv.get("projections", {})
                assert len(projections) > 0, f"Visual {v_name} ({v_type}) has no projections"

                proto = sv.get("prototypeQuery", {})
                assert proto.get("Version") == 2, (
                    f"Visual {v_name} prototypeQuery missing Version 2"
                )
                assert len(proto.get("From", [])) > 0, (
                    f"Visual {v_name} prototypeQuery missing From"
                )
                assert len(proto.get("Select", [])) > 0, (
                    f"Visual {v_name} prototypeQuery missing Select"
                )

                select_names = {s.get("Name") for s in proto.get("Select", [])}
                for _role, proj_list in projections.items():
                    for proj in proj_list:
                        qref = proj.get("queryRef")
                        assert qref in select_names, (
                            f"Visual {v_name}: projection {qref} not in prototypeQuery Select: {select_names}"
                        )

    assert total_visuals == 28, f"Expected 28 visuals across all pages, found {total_visuals}"


def test_date_dimension_and_sales_relationship_data_types():
    """Verify Date dimension and Sales relationship data types, M transformation, and 100% key match.

    Guards against Revenue by year_month displaying (Blank) due to dateTime vs string mismatch.
    """
    import csv

    # 1. Inspect dim_date.csv and enforce the schema shared by SQL, CSV, and PBIP.
    date_csv = POWERBI_DIR / "data" / "dim_date.csv"
    assert date_csv.exists(), "dim_date.csv not found"
    expected_date_columns = {
        "date_key",
        "year",
        "quarter",
        "quarter_name",
        "month",
        "month_name",
        "year_month",
        "day",
        "day_of_week",
        "day_name",
        "is_weekend",
    }
    with open(date_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert set(reader.fieldnames or []) == expected_date_columns, (
            f"Date columns must match the PBIP contract: {reader.fieldnames}"
        )
        date_rows = list(reader)

    from datetime import date, timedelta

    start_date = date(2023, 1, 1)
    end_date = date(2028, 12, 31)
    expected_date_keys = {
        (start_date + timedelta(days=offset)).isoformat()
        for offset in range((end_date - start_date).days + 1)
    }
    date_keys = {r["date_key"] for r in date_rows}
    assert len(date_rows) == len(expected_date_keys), (
        f"Expected one row per date from {start_date} through {end_date}; found {len(date_rows)} rows"
    )
    assert date_keys == expected_date_keys, (
        "Date dimension must cover every day from 2023-01-01 through 2028-12-31 exactly once"
    )
    for r in date_rows:
        assert r["year_month"], "year_month cannot be empty"

    # 2. Verify 100% Sales order_date foreign key coverage
    sales_csv = POWERBI_DIR / "data" / "vw_fact_sales.csv"
    assert sales_csv.exists(), "vw_fact_sales.csv not found"
    with open(sales_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sales_dates = [r["order_date"] for r in reader]

    assert len(sales_dates) == 34007
    missing_dates = set(sales_dates) - date_keys
    assert len(missing_dates) == 0, (
        f"Sales order_dates not found in Date dimension: {missing_dates}"
    )

    # 3. Verify model.bim column types and relationship
    model_file = POWERBI_DIR / "InsightFlow.SemanticModel" / "model.bim"
    with open(model_file, "r", encoding="utf-8") as f:
        bim_data = json.load(f)

    tables = {t["name"]: t for t in bim_data.get("model", {}).get("tables", [])}
    date_cols = {c["name"]: c for c in tables["Date"].get("columns", [])}
    sales_cols = {c["name"]: c for c in tables["Sales"].get("columns", [])}

    assert date_cols["date_key"].get("dataType") == "dateTime", "Date.date_key must be dateTime"
    assert sales_cols["order_date"].get("dataType") == "dateTime", (
        "Sales.order_date must be dateTime"
    )

    # 4. Verify Power Query M partition transforms in model.bim
    date_part = tables["Date"].get("partitions", [])[0]
    date_m_src = "\n".join(date_part.get("source", {}).get("expression", []))
    assert "TransformColumnTypes" in date_m_src, (
        "DatePartition missing TransformColumnTypes in model.bim"
    )
    assert '{"date_key", type date}' in date_m_src or '"date_key", type date' in date_m_src

    # 5. Verify TMDL Date table if present
    date_tmdl_file = (
        POWERBI_DIR / "InsightFlow.SemanticModel" / "definition" / "tables" / "Date.tmdl"
    )
    if date_tmdl_file.exists():
        tmdl_text = date_tmdl_file.read_text(encoding="utf-8")
        assert (
            "column date_key\n\t\tdataType: dateTime" in tmdl_text
            or "column date_key\r\n\t\tdataType: dateTime" in tmdl_text
        ), "Date.tmdl date_key must be dataType: dateTime"
        assert "TransformColumnTypes" in tmdl_text, (
            "Date.tmdl missing TransformColumnTypes in partition source"
        )


def test_data_assurance_reconciliation_model_and_powerquery_handling():
    """Verify DataQualityReconciliation numeric column types, DAX measures, and Power Query M transformation.

    Guards against 'The function SUM cannot work with values of type String' regression on Page 4.
    """
    model_file = POWERBI_DIR / "InsightFlow.SemanticModel" / "model.bim"
    with open(model_file, "r", encoding="utf-8") as f:
        bim_data = json.load(f)

    tables = {t["name"]: t for t in bim_data.get("model", {}).get("tables", [])}
    assert "DataQualityReconciliation" in tables, (
        "DataQualityReconciliation table missing from model.bim"
    )
    dqr_table = tables["DataQualityReconciliation"]
    dqr_cols = {c["name"]: c for c in dqr_table.get("columns", [])}

    # Verify column data types
    int_cols = [
        "raw_ingested",
        "exact_duplicates_dropped",
        "quarantined_rejected",
        "merged_deduplicated",
        "clean_loaded",
    ]
    for col in int_cols:
        assert col in dqr_cols, f"Column {col} missing from DataQualityReconciliation"
        assert dqr_cols[col].get("dataType") == "int64", (
            f"{col} must be int64, got {dqr_cols[col].get('dataType')}"
        )

    assert "preservation_rate" in dqr_cols
    assert dqr_cols["preservation_rate"].get("dataType") == "double", (
        "preservation_rate must be double"
    )

    # Verify M partition contains TransformColumnTypes
    partitions = dqr_table.get("partitions", [])
    assert len(partitions) >= 1
    m_expr = "\n".join(partitions[0].get("source", {}).get("expression", []))
    assert "TransformColumnTypes" in m_expr, "ReconciliationPartition missing TransformColumnTypes"
    assert "Int64.Type" in m_expr

    # Verify TMDL DataQualityReconciliation if exists
    dqr_tmdl = (
        POWERBI_DIR
        / "InsightFlow.SemanticModel"
        / "definition"
        / "tables"
        / "DataQualityReconciliation.tmdl"
    )
    if dqr_tmdl.exists():
        tmdl_text = dqr_tmdl.read_text(encoding="utf-8")
        assert (
            "column raw_ingested\n\t\tdataType: int64" in tmdl_text
            or "column raw_ingested\r\n\t\tdataType: int64" in tmdl_text
        )
        assert "TransformColumnTypes" in tmdl_text
