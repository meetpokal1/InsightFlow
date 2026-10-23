"""Generate the complete, modern Power BI Project (PBIP) structure for InsightFlow.

Creates:
  powerbi/InsightFlow.pbip
  powerbi/InsightFlow.Report/definition.pbir
  powerbi/InsightFlow.Report/report.json
  powerbi/InsightFlow.SemanticModel/definition.pbism
  powerbi/InsightFlow.SemanticModel/model.bim
"""

import json
import pathlib
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
POWERBI_DIR = PROJECT_ROOT / "powerbi"
DATA_DIR = POWERBI_DIR / "data"
REPORT_DIR = POWERBI_DIR / "InsightFlow.Report"
MODEL_DIR = POWERBI_DIR / "InsightFlow.SemanticModel"


def build_pbip(clean_cache: bool = False):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    # Clean stale Analysis Services cache only when explicitly requested (e.g. during schema type migration)
    if clean_cache:
        cache_abf = MODEL_DIR / ".pbi" / "cache.abf"
        if cache_abf.exists():
            cache_abf.unlink()
        local_settings = MODEL_DIR / ".pbi" / "localSettings.json"
        if local_settings.exists():
            local_settings.unlink()

    data_folder_resolved = str(DATA_DIR.resolve()).replace("/", "\\")

    # 1. Root InsightFlow.pbip (standard Microsoft PBIP 1.0 schema)
    pbip_data = {
        "version": "1.0",
        "artifacts": [
            {
                "report": {
                    "path": "InsightFlow.Report"
                }
            }
        ]
    }
    with open(POWERBI_DIR / "InsightFlow.pbip", "w", encoding="utf-8") as f:
        json.dump(pbip_data, f, indent=2)

    # 2. Report definition.pbir (standard Fabric PBIR definitionProperties 1.0 schema)
    pbir_data = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json",
        "version": "1.0",
        "datasetReference": {
            "byPath": {
                "path": "../InsightFlow.SemanticModel"
            },
            "byConnection": None
        }
    }
    with open(REPORT_DIR / "definition.pbir", "w", encoding="utf-8") as f:
        json.dump(pbir_data, f, indent=2)

    # 3. Semantic model definition.pbism (standard Fabric semanticModel definitionProperties 1.0 schema)
    pbism_data = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "1.0"
    }
    with open(MODEL_DIR / "definition.pbism", "w", encoding="utf-8") as f:
        json.dump(pbism_data, f, indent=2)

    # 4. Semantic model model.bim
    model_bim = {
        "name": "InsightFlowSemanticModel",
        "compatibilityLevel": 1606,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {
                "legacyRedirects": True,
                "returnErrorValuesAsNull": True
            },
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "en-IN",
            "expressions": [
                {
                    "name": "DataFolder",
                    "kind": "m",
                    "expression": [
                        f'"{data_folder_resolved}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'
                    ],
                    "lineageTag": "60a4f6bb-74f7-4dc5-b467-3dd30f555021",
                    "annotations": [
                        {
                            "name": "PBI_NavigationStepName",
                            "value": "Navigation"
                        },
                        {
                            "name": "PBI_ResultType",
                            "value": "Text"
                        }
                    ]
                }
            ],
            "tables": [
                {
                    "name": "Sales",
                    "description": "Line-level completed order transactions",
                    "columns": [
                        {"name": "order_item_id", "dataType": "string", "sourceColumn": "order_item_id"},
                        {"name": "order_id", "dataType": "string", "sourceColumn": "order_id"},
                        {"name": "order_date", "dataType": "dateTime", "sourceColumn": "order_date", "formatString": "yyyy-mm-dd"},
                        {"name": "customer_id", "dataType": "string", "sourceColumn": "customer_id"},
                        {"name": "location_id", "dataType": "string", "sourceColumn": "location_id"},
                        {"name": "product_id", "dataType": "string", "sourceColumn": "product_id"},
                        {"name": "quantity", "dataType": "int64", "sourceColumn": "quantity", "formatString": "#,0"},
                        {"name": "unit_price", "dataType": "double", "sourceColumn": "unit_price", "formatString": "\"₹\"#,##0.00"},
                        {"name": "discount_pct", "dataType": "double", "sourceColumn": "discount_pct", "formatString": "0.0%"},
                        {"name": "net_revenue", "dataType": "double", "sourceColumn": "net_revenue", "formatString": "\"₹\"#,##0.00"},
                        {"name": "cost_of_goods", "dataType": "double", "sourceColumn": "cost_of_goods", "formatString": "\"₹\"#,##0.00"},
                        {"name": "gross_profit", "dataType": "double", "sourceColumn": "gross_profit", "formatString": "\"₹\"#,##0.00"}
                    ],
                    "measures": [
                        {
                            "name": "Revenue",
                            "expression": "SUM(Sales[net_revenue])",
                            "formatString": "\"₹\"#,##0",
                            "description": "Total net revenue across completed customer orders"
                        },
                        {
                            "name": "Cost of Goods",
                            "expression": "SUM(Sales[cost_of_goods])",
                            "formatString": "\"₹\"#,##0",
                            "description": "Total catalog cost of goods sold"
                        },
                        {
                            "name": "Gross Profit",
                            "expression": "[Revenue] - [Cost of Goods]",
                            "formatString": "\"₹\"#,##0",
                            "description": "Gross margin profit contribution (Revenue - COGS)"
                        },
                        {
                            "name": "Gross Margin %",
                            "expression": "DIVIDE([Gross Profit], [Revenue])",
                            "formatString": "0.0%",
                            "description": "Gross profit percentage of net revenue"
                        },
                        {
                            "name": "Orders",
                            "expression": "DISTINCTCOUNT(Sales[order_id])",
                            "formatString": "#,0",
                            "description": "Count of distinct completed orders"
                        },
                        {
                            "name": "Average Order Value",
                            "expression": "DIVIDE([Revenue], [Orders])",
                            "formatString": "\"₹\"#,##0",
                            "description": "Net revenue per completed order"
                        },
                        {
                            "name": "Units Sold",
                            "expression": "SUM(Sales[quantity])",
                            "formatString": "#,0",
                            "description": "Total item units sold"
                        },
                        {
                            "name": "Active Customers",
                            "expression": "DISTINCTCOUNT(Sales[customer_id])",
                            "formatString": "#,0",
                            "description": "Distinct buying customers"
                        },
                        {
                            "name": "Basmati Rice Net Revenue",
                            "expression": "CALCULATE([Revenue], Product[product_id] = \"P0010\")",
                            "formatString": "\"₹\"#,##0",
                            "description": "Net revenue for flagship product P0010 Basmati Rice 5kg"
                        },
                        {
                            "name": "Basmati Rice Gross Profit",
                            "expression": "CALCULATE([Gross Profit], Product[product_id] = \"P0010\")",
                            "formatString": "\"₹\"#,##0",
                            "description": "Gross profit for flagship product P0010 Basmati Rice 5kg"
                        },
                        {
                            "name": "Basmati Rice Margin %",
                            "expression": "CALCULATE([Gross Margin %], Product[product_id] = \"P0010\")",
                            "formatString": "0.0%",
                            "description": "Gross margin for flagship product P0010 Basmati Rice 5kg (2.15%)"
                        },
                        {
                            "name": "Basmati Break Even Volume Decline %",
                            "expression": "1 - DIVIDE(CALCULATE([Gross Profit], Product[product_id] = \"P0010\"), (CALCULATE([Revenue], Product[product_id] = \"P0010\") * 1.03) - CALCULATE([Cost of Goods], Product[product_id] = \"P0010\"))",
                            "formatString": "0.0%",
                            "description": "Break-even volume decline tolerance for Basmati Rice at +3% price increase (58.3%)"
                        }
                    ],
                    "partitions": [
                        {
                            "name": "SalesPartition",
                            "source": {
                                "type": "m",
                                "expression": [
                                    "let",
                                    "    FolderPath = if Text.EndsWith(DataFolder, \"\\\") or Text.EndsWith(DataFolder, \"/\") then DataFolder else DataFolder & \"\\\",",
                                    "    Source = Csv.Document(File.Contents(FolderPath & \"vw_fact_sales.csv\"), [Delimiter=\",\", Columns=12, Encoding=65001, QuoteStyle=QuoteStyle.None]),",
                                    "    #\"Promoted Headers\" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
                                    "    #\"Changed Type\" = Table.TransformColumnTypes(#\"Promoted Headers\",{{\"order_item_id\", type text}, {\"order_id\", type text}, {\"order_date\", type date}, {\"customer_id\", type text}, {\"location_id\", type text}, {\"product_id\", type text}, {\"quantity\", Int64.Type}, {\"unit_price\", type number}, {\"discount_pct\", type number}, {\"net_revenue\", type number}, {\"cost_of_goods\", type number}, {\"gross_profit\", type number}})",
                                    "in",
                                    "    #\"Changed Type\""
                                ]
                            }
                        }
                    ]
                },
                {
                    "name": "Inventory",
                    "description": "Stock snapshot and buffer replenishment metrics as of 30 Sept 2026",
                    "columns": [
                        {"name": "inventory_id", "dataType": "string", "sourceColumn": "inventory_id"},
                        {"name": "product_id", "dataType": "string", "sourceColumn": "product_id"},
                        {"name": "location_id", "dataType": "string", "sourceColumn": "location_id"},
                        {"name": "snapshot_date", "dataType": "dateTime", "sourceColumn": "snapshot_date", "formatString": "yyyy-mm-dd"},
                        {"name": "quantity_on_hand", "dataType": "int64", "sourceColumn": "quantity_on_hand", "formatString": "#,0"},
                        {"name": "reorder_level", "dataType": "int64", "sourceColumn": "reorder_level", "formatString": "#,0"},
                        {"name": "last_restocked_date", "dataType": "dateTime", "sourceColumn": "last_restocked_date", "formatString": "yyyy-mm-dd"},
                        {"name": "lead_time_days", "dataType": "int64", "sourceColumn": "lead_time_days"},
                        {"name": "cost_price", "dataType": "double", "sourceColumn": "cost_price"},
                        {"name": "selling_price", "dataType": "double", "sourceColumn": "selling_price"},
                        {"name": "inventory_value", "dataType": "double", "sourceColumn": "inventory_value", "formatString": "\"₹\"#,##0.00"},
                        {"name": "units_sold_90d", "dataType": "int64", "sourceColumn": "units_sold_90d"},
                        {"name": "avg_daily_units", "dataType": "double", "sourceColumn": "avg_daily_units"},
                        {"name": "days_of_cover", "dataType": "double", "sourceColumn": "days_of_cover"},
                        {"name": "stock_status", "dataType": "string", "sourceColumn": "stock_status"},
                        {"name": "suggested_order_qty", "dataType": "int64", "sourceColumn": "suggested_order_qty"},
                        {"name": "replenishment_quantity_required", "dataType": "int64", "sourceColumn": "replenishment_quantity_required", "formatString": "#,0"},
                        {"name": "replenishment_cost_estimate", "dataType": "double", "sourceColumn": "replenishment_cost_estimate", "formatString": "\"₹\"#,##0.00"},
                        {"name": "stock_gap_retail_valuation", "dataType": "double", "sourceColumn": "stock_gap_retail_valuation", "formatString": "\"₹\"#,##0.00"},
                        {"name": "is_stockout", "dataType": "boolean", "sourceColumn": "is_stockout"},
                        {"name": "is_below_reorder", "dataType": "boolean", "sourceColumn": "is_below_reorder"}
                    ],
                    "measures": [
                        {
                            "name": "Stock Value",
                            "expression": "SUM(Inventory[inventory_value])",
                            "formatString": "\"₹\"#,##0",
                            "description": "Total valuation of stock on hand at cost price (₹22.49M)"
                        },
                        {
                            "name": "Stock Positions",
                            "expression": "COUNTROWS(Inventory)",
                            "formatString": "#,0",
                            "description": "Total tracked product-location inventory positions (449)"
                        },
                        {
                            "name": "Days of Cover",
                            "expression": "AVERAGE(Inventory[days_of_cover])",
                            "formatString": "0.0",
                            "description": "Average days of stock cover based on 90-day run rate"
                        },
                        {
                            "name": "Items Needing Action",
                            "expression": "CALCULATE(COUNTROWS(Inventory), Inventory[stock_status] IN {\"Out of stock\", \"Stock-out risk\", \"Low stock\"})",
                            "formatString": "#,0",
                            "description": "Positions requiring purchasing review (92)"
                        },
                        {
                            "name": "Stockout Positions",
                            "expression": "CALCULATE(COUNTROWS(Inventory), Inventory[quantity_on_hand] = 0)",
                            "formatString": "#,0",
                            "description": "True out of stock positions with 0 units on hand (40 positions)"
                        },
                        {
                            "name": "Positions Below Reorder",
                            "expression": "CALCULATE(COUNTROWS(Inventory), Inventory[quantity_on_hand] < Inventory[reorder_level])",
                            "formatString": "#,0",
                            "description": "Positions where stock is below reorder threshold (96 positions)"
                        },
                        {
                            "name": "Replenishment Qty Required",
                            "expression": "SUM(Inventory[replenishment_quantity_required])",
                            "formatString": "#,0",
                            "description": "Total units required to restore depleted buffers to reorder level (5,791 units)"
                        },
                        {
                            "name": "Replenishment Cost Estimate",
                            "expression": "SUM(Inventory[replenishment_cost_estimate])",
                            "formatString": "\"₹\"#,##0",
                            "description": "Working capital required at purchase cost to restore buffer stock (₹9.66 L)"
                        },
                        {
                            "name": "Stock Gap Retail Valuation",
                            "expression": "SUM(Inventory[stock_gap_retail_valuation])",
                            "formatString": "\"₹\"#,##0",
                            "description": "Catalog retail valuation of buffer deficit units; NOT lost revenue (₹13.41 L)"
                        }
                    ],
                    "partitions": [
                        {
                            "name": "InventoryPartition",
                            "source": {
                                "type": "m",
                                "expression": [
                                    "let",
                                    "    FolderPath = if Text.EndsWith(DataFolder, \"\\\") or Text.EndsWith(DataFolder, \"/\") then DataFolder else DataFolder & \"\\\",",
                                    "    Source = Csv.Document(File.Contents(FolderPath & \"vw_fact_inventory.csv\"), [Delimiter=\",\", Columns=21, Encoding=65001, QuoteStyle=QuoteStyle.None]),",
                                    "    #\"Promoted Headers\" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
                                    "    #\"Replaced Blank Dates\" = Table.ReplaceValue(#\"Promoted Headers\", \"\", null, Replacer.ReplaceValue, {\"last_restocked_date\", \"days_of_cover\"}),",
                                    "    #\"Changed Type\" = Table.TransformColumnTypes(#\"Replaced Blank Dates\", {{\"inventory_id\", type text}, {\"product_id\", type text}, {\"location_id\", type text}, {\"snapshot_date\", type date}, {\"quantity_on_hand\", Int64.Type}, {\"reorder_level\", Int64.Type}, {\"last_restocked_date\", type date}, {\"lead_time_days\", Int64.Type}, {\"cost_price\", type number}, {\"selling_price\", type number}, {\"inventory_value\", type number}, {\"units_sold_90d\", Int64.Type}, {\"avg_daily_units\", type number}, {\"days_of_cover\", type number}, {\"stock_status\", type text}, {\"suggested_order_qty\", Int64.Type}, {\"replenishment_quantity_required\", Int64.Type}, {\"replenishment_cost_estimate\", type number}, {\"stock_gap_retail_valuation\", type number}, {\"is_stockout\", type logical}, {\"is_below_reorder\", type logical}}, \"en-US\")",
                                    "in",
                                    "    #\"Changed Type\""
                                ]
                            }
                        }
                    ]
                },
                {
                    "name": "Product",
                    "description": "Product catalog dimension",
                    "columns": [
                        {"name": "product_id", "dataType": "string", "sourceColumn": "product_id"},
                        {"name": "product_name", "dataType": "string", "sourceColumn": "product_name"},
                        {"name": "category_id", "dataType": "string", "sourceColumn": "category_id"},
                        {"name": "category_name", "dataType": "string", "sourceColumn": "category_name"},
                        {"name": "supplier_id", "dataType": "string", "sourceColumn": "supplier_id"},
                        {"name": "supplier_name", "dataType": "string", "sourceColumn": "supplier_name"},
                        {"name": "lead_time_days", "dataType": "int64", "sourceColumn": "lead_time_days"},
                        {"name": "unit", "dataType": "string", "sourceColumn": "unit"},
                        {"name": "cost_price", "dataType": "double", "sourceColumn": "cost_price"},
                        {"name": "selling_price", "dataType": "double", "sourceColumn": "selling_price"},
                        {"name": "list_margin_pct", "dataType": "double", "sourceColumn": "list_margin_pct", "formatString": "0.0%"}
                    ],
                    "partitions": [
                        {
                            "name": "ProductPartition",
                            "source": {
                                "type": "m",
                                "expression": [
                                    "let",
                                    "    FolderPath = if Text.EndsWith(DataFolder, \"\\\") or Text.EndsWith(DataFolder, \"/\") then DataFolder else DataFolder & \"\\\",",
                                    "    Source = Csv.Document(File.Contents(FolderPath & \"vw_dim_product.csv\"), [Delimiter=\",\", Columns=11, Encoding=65001, QuoteStyle=QuoteStyle.None]),",
                                    "    #\"Promoted Headers\" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])",
                                    "in",
                                    "    #\"Promoted Headers\""
                                ]
                            }
                        }
                    ]
                },
                {
                    "name": "Customer",
                    "description": "Customer dimension with RFM segmentation",
                    "columns": [
                        {"name": "customer_id", "dataType": "string", "sourceColumn": "customer_id"},
                        {"name": "customer_name", "dataType": "string", "sourceColumn": "customer_name"},
                        {"name": "city", "dataType": "string", "sourceColumn": "city"},
                        {"name": "customer_type", "dataType": "string", "sourceColumn": "customer_type"},
                        {"name": "signup_date", "dataType": "dateTime", "sourceColumn": "signup_date", "formatString": "yyyy-mm-dd"},
                        {"name": "first_order_date", "dataType": "dateTime", "sourceColumn": "first_order_date", "formatString": "yyyy-mm-dd"},
                        {"name": "last_order_date", "dataType": "dateTime", "sourceColumn": "last_order_date", "formatString": "yyyy-mm-dd"},
                        {"name": "segment", "dataType": "string", "sourceColumn": "segment"}
                    ],
                    "partitions": [
                        {
                            "name": "CustomerPartition",
                            "source": {
                                "type": "m",
                                "expression": [
                                    "let",
                                    "    FolderPath = if Text.EndsWith(DataFolder, \"\\\") or Text.EndsWith(DataFolder, \"/\") then DataFolder else DataFolder & \"\\\",",
                                    "    Source = Csv.Document(File.Contents(FolderPath & \"vw_dim_customer.csv\"), [Delimiter=\",\", Columns=8, Encoding=65001, QuoteStyle=QuoteStyle.None]),",
                                    "    #\"Promoted Headers\" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
                                    "    #\"Replaced Blank Dates\" = Table.ReplaceValue(#\"Promoted Headers\", \"\", null, Replacer.ReplaceValue, {\"signup_date\", \"first_order_date\", \"last_order_date\"}),",
                                    "    #\"Changed Type\" = Table.TransformColumnTypes(#\"Replaced Blank Dates\", {{\"customer_id\", type text}, {\"customer_name\", type text}, {\"city\", type text}, {\"customer_type\", type text}, {\"signup_date\", type date}, {\"first_order_date\", type date}, {\"last_order_date\", type date}, {\"segment\", type text}}, \"en-US\")",
                                    "in",
                                    "    #\"Changed Type\""
                                ]
                            }
                        }
                    ]
                },
                {
                    "name": "Location",
                    "description": "Store and warehouse locations",
                    "columns": [
                        {"name": "location_id", "dataType": "string", "sourceColumn": "location_id"},
                        {"name": "location_name", "dataType": "string", "sourceColumn": "location_name"},
                        {"name": "city", "dataType": "string", "sourceColumn": "city"},
                        {"name": "state", "dataType": "string", "sourceColumn": "state"},
                        {"name": "region", "dataType": "string", "sourceColumn": "region"},
                        {"name": "location_type", "dataType": "string", "sourceColumn": "location_type"}
                    ],
                    "partitions": [
                        {
                            "name": "LocationPartition",
                            "source": {
                                "type": "m",
                                "expression": [
                                    "let",
                                    "    FolderPath = if Text.EndsWith(DataFolder, \"\\\") or Text.EndsWith(DataFolder, \"/\") then DataFolder else DataFolder & \"\\\",",
                                    "    Source = Csv.Document(File.Contents(FolderPath & \"vw_dim_location.csv\"), [Delimiter=\",\", Columns=6, Encoding=65001, QuoteStyle=QuoteStyle.None]),",
                                    "    #\"Promoted Headers\" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])",
                                    "in",
                                    "    #\"Promoted Headers\""
                                ]
                            }
                        }
                    ]
                },
                {
                    "name": "Date",
                    "description": "Marked calendar date dimension",
                    "dataCategory": "Time",
                    "columns": [
                        {"name": "date_key", "dataType": "dateTime", "sourceColumn": "date_key", "formatString": "yyyy-mm-dd", "isKey": True},
                        {"name": "year", "dataType": "int64", "sourceColumn": "year"},
                        {"name": "quarter", "dataType": "int64", "sourceColumn": "quarter"},
                        {"name": "quarter_name", "dataType": "string", "sourceColumn": "quarter_name"},
                        {"name": "month", "dataType": "int64", "sourceColumn": "month"},
                        {"name": "month_name", "dataType": "string", "sourceColumn": "month_name"},
                        {"name": "year_month", "dataType": "string", "sourceColumn": "year_month"},
                        {"name": "day", "dataType": "int64", "sourceColumn": "day"},
                        {"name": "day_of_week", "dataType": "int64", "sourceColumn": "day_of_week"},
                        {"name": "day_name", "dataType": "string", "sourceColumn": "day_name"},
                        {"name": "is_weekend", "dataType": "boolean", "sourceColumn": "is_weekend"}
                    ],
                    "partitions": [
                        {
                            "name": "DatePartition",
                            "source": {
                                "type": "m",
                                "expression": [
                                    "let",
                                    "    FolderPath = if Text.EndsWith(DataFolder, \"\\\") or Text.EndsWith(DataFolder, \"/\") then DataFolder else DataFolder & \"\\\",",
                                    "    Source = Csv.Document(File.Contents(FolderPath & \"dim_date.csv\"), [Delimiter=\",\", Columns=11, Encoding=65001, QuoteStyle=QuoteStyle.None]),",
                                    "    #\"Promoted Headers\" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
                                    "    #\"Changed Type\" = Table.TransformColumnTypes(#\"Promoted Headers\", {{\"date_key\", type date}, {\"year\", Int64.Type}, {\"quarter\", Int64.Type}, {\"quarter_name\", type text}, {\"month\", Int64.Type}, {\"month_name\", type text}, {\"year_month\", type text}, {\"day\", Int64.Type}, {\"day_of_week\", Int64.Type}, {\"day_name\", type text}, {\"is_weekend\", type logical}}, \"en-US\")",
                                    "in",
                                    "    #\"Changed Type\""
                                ]
                            }
                        }
                    ]
                },
                {
                    "name": "DataQualityReconciliation",
                    "description": "Pipeline data assurance reconciliation matrix",
                    "columns": [
                        {"name": "table_name", "dataType": "string", "sourceColumn": "table_name"},
                        {"name": "raw_ingested", "dataType": "int64", "sourceColumn": "raw_ingested", "formatString": "#,0"},
                        {"name": "exact_duplicates_dropped", "dataType": "int64", "sourceColumn": "exact_duplicates_dropped", "formatString": "#,0"},
                        {"name": "quarantined_rejected", "dataType": "int64", "sourceColumn": "quarantined_rejected", "formatString": "#,0"},
                        {"name": "merged_deduplicated", "dataType": "int64", "sourceColumn": "merged_deduplicated", "formatString": "#,0"},
                        {"name": "clean_loaded", "dataType": "int64", "sourceColumn": "clean_loaded", "formatString": "#,0"},
                        {"name": "reconciliation_status", "dataType": "string", "sourceColumn": "reconciliation_status"},
                        {"name": "preservation_rate", "dataType": "double", "sourceColumn": "preservation_rate", "formatString": "0.0%"}
                    ],
                    "measures": [
                        {
                            "name": "Total Raw Records",
                            "expression": "SUM(DataQualityReconciliation[raw_ingested])",
                            "formatString": "#,0"
                        },
                        {
                            "name": "Total Clean Records",
                            "expression": "SUM(DataQualityReconciliation[clean_loaded])",
                            "formatString": "#,0"
                        },
                        {
                            "name": "Total Duplicate Records",
                            "expression": "SUM(DataQualityReconciliation[exact_duplicates_dropped])",
                            "formatString": "#,0"
                        },
                        {
                            "name": "Total Quarantined Records",
                            "expression": "SUM(DataQualityReconciliation[quarantined_rejected])",
                            "formatString": "#,0"
                        },
                        {
                            "name": "Overall Preservation Rate %",
                            "expression": "DIVIDE([Total Clean Records], [Total Raw Records])",
                            "formatString": "0.0%"
                        }
                    ],
                    "partitions": [
                        {
                            "name": "ReconciliationPartition",
                            "source": {
                                "type": "m",
                                "expression": [
                                    "let",
                                    "    FolderPath = if Text.EndsWith(DataFolder, \"\\\") or Text.EndsWith(DataFolder, \"/\") then DataFolder else DataFolder & \"\\\",",
                                    "    Source = Csv.Document(File.Contents(FolderPath & \"data_assurance_reconciliation.csv\"), [Delimiter=\",\", Columns=8, Encoding=65001, QuoteStyle=QuoteStyle.None]),",
                                    "    #\"Promoted Headers\" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
                                    "    #\"Changed Type\" = Table.TransformColumnTypes(#\"Promoted Headers\", {{\"table_name\", type text}, {\"raw_ingested\", Int64.Type}, {\"exact_duplicates_dropped\", Int64.Type}, {\"quarantined_rejected\", Int64.Type}, {\"merged_deduplicated\", Int64.Type}, {\"clean_loaded\", Int64.Type}, {\"reconciliation_status\", type text}, {\"preservation_rate\", type number}}, \"en-US\")",
                                    "in",
                                    "    #\"Changed Type\""
                                ]
                            }
                        }
                    ]
                }
            ],
            "relationships": [
                {
                    "name": "Sales_Product",
                    "fromTable": "Sales",
                    "fromColumn": "product_id",
                    "toTable": "Product",
                    "toColumn": "product_id"
                },
                {
                    "name": "Sales_Customer",
                    "fromTable": "Sales",
                    "fromColumn": "customer_id",
                    "toTable": "Customer",
                    "toColumn": "customer_id"
                },
                {
                    "name": "Sales_Location",
                    "fromTable": "Sales",
                    "fromColumn": "location_id",
                    "toTable": "Location",
                    "toColumn": "location_id"
                },
                {
                    "name": "Sales_Date",
                    "fromTable": "Sales",
                    "fromColumn": "order_date",
                    "toTable": "Date",
                    "toColumn": "date_key"
                },
                {
                    "name": "Inventory_Product",
                    "fromTable": "Inventory",
                    "fromColumn": "product_id",
                    "toTable": "Product",
                    "toColumn": "product_id"
                },
                {
                    "name": "Inventory_Location",
                    "fromTable": "Inventory",
                    "fromColumn": "location_id",
                    "toTable": "Location",
                    "toColumn": "location_id"
                }
            ]
        }
    }
    model_bim_file = MODEL_DIR / "model.bim"
    if model_bim_file.exists():
        with open(model_bim_file, "r", encoding="utf-8") as f:
            existing_bim = json.load(f)
        existing_bim.setdefault("model", {})
        existing_bim["model"]["expressions"] = model_bim["model"]["expressions"]
        partition_map = {t["name"]: t["partitions"] for t in model_bim["model"]["tables"]}
        column_map = {t["name"]: t["columns"] for t in model_bim["model"]["tables"]}
        for t in existing_bim["model"].get("tables", []):
            if t["name"] in partition_map:
                t["partitions"] = partition_map[t["name"]]
            if t["name"] in column_map:
                t["columns"] = column_map[t["name"]]
        with open(model_bim_file, "w", encoding="utf-8") as f:
            json.dump(existing_bim, f, indent=2)
    else:
        with open(model_bim_file, "w", encoding="utf-8") as f:
            json.dump(model_bim, f, indent=2)

    # 5. Report report.json
    report_json = {
        "config": json.dumps({
            "version": "5.53",
            "themeCollection": {
                "baseTheme": {
                    "name": "CY24SU10",
                    "version": "5.53",
                    "type": 2
                }
            },
            "activeSectionIndex": 0
        }),
        "layoutOptimization": 0,
        "sections": [
            {
                "name": "ReportSection_ExecProfitability",
                "displayName": "Executive Profitability",
                "width": 1280,
                "height": 720,
                "config": json.dumps({"visibility": 0}),
                "visualContainers": [
                    {
                        "x": 20, "y": 20, "width": 1240, "height": 50,
                        "config": json.dumps({
                            "name": "PageHeader",
                            "singleVisual": {
                                "visualType": "textbox",
                                "general": {"title": "Executive Profitability Overview"}
                            }
                        })
                    },
                    {
                        "x": 20, "y": 80, "width": 230, "height": 110,
                        "config": json.dumps({
                            "name": "CardRevenue",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Sales.Revenue"}]}
                            }
                        })
                    },
                    {
                        "x": 270, "y": 80, "width": 230, "height": 110,
                        "config": json.dumps({
                            "name": "CardGrossProfit",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Sales.Gross Profit"}]}
                            }
                        })
                    },
                    {
                        "x": 520, "y": 80, "width": 230, "height": 110,
                        "config": json.dumps({
                            "name": "CardGrossMargin",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Sales.Gross Margin %"}]}
                            }
                        })
                    },
                    {
                        "x": 770, "y": 80, "width": 230, "height": 110,
                        "config": json.dumps({
                            "name": "CardOrders",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Sales.Orders"}]}
                            }
                        })
                    },
                    {
                        "x": 1020, "y": 80, "width": 240, "height": 110,
                        "config": json.dumps({
                            "name": "CardAOV",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Sales.Average Order Value"}]}
                            }
                        })
                    },
                    {
                        "x": 20, "y": 210, "width": 780, "height": 480,
                        "config": json.dumps({
                            "name": "MonthlyRevenueTrend",
                            "singleVisual": {
                                "visualType": "lineChart",
                                "projections": {
                                    "Category": [{"queryRef": "Date.year_month"}],
                                    "Y": [{"queryRef": "Sales.Revenue"}]
                                }
                            }
                        })
                    },
                    {
                        "x": 820, "y": 210, "width": 440, "height": 480,
                        "config": json.dumps({
                            "name": "CategoryRevenueBreakdown",
                            "singleVisual": {
                                "visualType": "barChart",
                                "projections": {
                                    "Category": [{"queryRef": "Product.category_name"}],
                                    "Y": [{"queryRef": "Sales.Revenue"}]
                                }
                            }
                        })
                    }
                ]
            },
            {
                "name": "ReportSection_MarginInvestigation",
                "displayName": "Margin Investigation",
                "width": 1280,
                "height": 720,
                "config": json.dumps({"visibility": 0}),
                "visualContainers": [
                    {
                        "x": 20, "y": 20, "width": 1240, "height": 50,
                        "config": json.dumps({
                            "name": "HeaderMargin",
                            "singleVisual": {
                                "visualType": "textbox",
                                "general": {"title": "Margin Investigation & Flagship Case Study (Basmati Rice)"}
                            }
                        })
                    },
                    {
                        "x": 20, "y": 80, "width": 290, "height": 110,
                        "config": json.dumps({
                            "name": "CardBasmatiRev",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Sales.Basmati Rice Net Revenue"}]}
                            }
                        })
                    },
                    {
                        "x": 330, "y": 80, "width": 290, "height": 110,
                        "config": json.dumps({
                            "name": "CardBasmatiGP",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Sales.Basmati Rice Gross Profit"}]}
                            }
                        })
                    },
                    {
                        "x": 640, "y": 80, "width": 290, "height": 110,
                        "config": json.dumps({
                            "name": "CardBasmatiMargin",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Sales.Basmati Rice Margin %"}]}
                            }
                        })
                    },
                    {
                        "x": 950, "y": 80, "width": 310, "height": 110,
                        "config": json.dumps({
                            "name": "CardBasmatiTolerance",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Sales.Basmati Break Even Volume Decline %"}]}
                            }
                        })
                    },
                    {
                        "x": 20, "y": 210, "width": 780, "height": 480,
                        "config": json.dumps({
                            "name": "MarginScatter",
                            "singleVisual": {
                                "visualType": "scatterChart",
                                "projections": {
                                    "X": [{"queryRef": "Sales.Revenue"}],
                                    "Y": [{"queryRef": "Sales.Gross Profit"}],
                                    "Details": [{"queryRef": "Product.product_name"}]
                                }
                            }
                        })
                    },
                    {
                        "x": 820, "y": 210, "width": 440, "height": 480,
                        "config": json.dumps({
                            "name": "SupplierMarginRanking",
                            "singleVisual": {
                                "visualType": "barChart",
                                "projections": {
                                    "Category": [{"queryRef": "Product.supplier_name"}],
                                    "Y": [{"queryRef": "Sales.Gross Margin %"}]
                                }
                            }
                        })
                    }
                ]
            },
            {
                "name": "ReportSection_InventoryDecisions",
                "displayName": "Inventory Decisions",
                "width": 1280,
                "height": 720,
                "config": json.dumps({"visibility": 0}),
                "visualContainers": [
                    {
                        "x": 20, "y": 20, "width": 1240, "height": 50,
                        "config": json.dumps({
                            "name": "HeaderInventory",
                            "singleVisual": {
                                "visualType": "textbox",
                                "general": {"title": "Inventory Intelligence & Capital Replenishment"}
                            }
                        })
                    },
                    {
                        "x": 20, "y": 80, "width": 230, "height": 110,
                        "config": json.dumps({
                            "name": "CardStockVal",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Inventory.Stock Value"}]}
                            }
                        })
                    },
                    {
                        "x": 270, "y": 80, "width": 230, "height": 110,
                        "config": json.dumps({
                            "name": "CardStockouts",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Inventory.Stockout Positions"}]}
                            }
                        })
                    },
                    {
                        "x": 520, "y": 80, "width": 230, "height": 110,
                        "config": json.dumps({
                            "name": "CardBelowReorder",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Inventory.Positions Below Reorder"}]}
                            }
                        })
                    },
                    {
                        "x": 770, "y": 80, "width": 230, "height": 110,
                        "config": json.dumps({
                            "name": "CardReplenishCost",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Inventory.Replenishment Cost Estimate"}]}
                            }
                        })
                    },
                    {
                        "x": 1020, "y": 80, "width": 240, "height": 110,
                        "config": json.dumps({
                            "name": "CardStockGapRetail",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "Inventory.Stock Gap Retail Valuation"}]}
                            }
                        })
                    },
                    {
                        "x": 20, "y": 210, "width": 580, "height": 480,
                        "config": json.dumps({
                            "name": "StockStatusMix",
                            "singleVisual": {
                                "visualType": "pieChart",
                                "projections": {
                                    "Category": [{"queryRef": "Inventory.stock_status"}],
                                    "Y": [{"queryRef": "Inventory.Stock Positions"}]
                                }
                            }
                        })
                    },
                    {
                        "x": 620, "y": 210, "width": 640, "height": 480,
                        "config": json.dumps({
                            "name": "ReplenishmentQueueTable",
                            "singleVisual": {
                                "visualType": "tableEx",
                                "projections": {
                                    "Values": [
                                        {"queryRef": "Product.product_name"},
                                        {"queryRef": "Location.location_name"},
                                        {"queryRef": "Inventory.quantity_on_hand"},
                                        {"queryRef": "Inventory.reorder_level"},
                                        {"queryRef": "Inventory.Replenishment Qty Required"},
                                        {"queryRef": "Inventory.Replenishment Cost Estimate"}
                                    ]
                                }
                            }
                        })
                    }
                ]
            },
            {
                "name": "ReportSection_DataIntegrity",
                "displayName": "Data Integrity & Pipeline Assurance",
                "width": 1280,
                "height": 720,
                "config": json.dumps({"visibility": 0}),
                "visualContainers": [
                    {
                        "x": 20, "y": 15, "width": 1240, "height": 45,
                        "config": json.dumps({
                            "name": "HeaderIntegrity",
                            "singleVisual": {
                                "visualType": "textbox",
                                "general": {"title": "Data Pipeline Assurance & Conservation Reconciliation Matrix"}
                            }
                        })
                    },
                    {
                        "x": 20, "y": 65, "width": 235, "height": 95,
                        "config": json.dumps({
                            "name": "CardTotalRaw",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "DataQualityReconciliation.Total Raw Records"}]}
                            }
                        })
                    },
                    {
                        "x": 270, "y": 65, "width": 235, "height": 95,
                        "config": json.dumps({
                            "name": "CardTotalClean",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "DataQualityReconciliation.Total Clean Records"}]}
                            }
                        })
                    },
                    {
                        "x": 520, "y": 65, "width": 235, "height": 95,
                        "config": json.dumps({
                            "name": "CardDuplicates",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "DataQualityReconciliation.Total Duplicate Records"}]}
                            }
                        })
                    },
                    {
                        "x": 770, "y": 65, "width": 235, "height": 95,
                        "config": json.dumps({
                            "name": "CardQuarantined",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "DataQualityReconciliation.Total Quarantined Records"}]}
                            }
                        })
                    },
                    {
                        "x": 1020, "y": 65, "width": 240, "height": 95,
                        "config": json.dumps({
                            "name": "CardPreservationRate",
                            "singleVisual": {
                                "visualType": "card",
                                "projections": {"Values": [{"queryRef": "DataQualityReconciliation.Overall Preservation Rate %"}]}
                            }
                        })
                    },
                    {
                        "x": 20, "y": 175, "width": 780, "height": 525,
                        "config": json.dumps({
                            "name": "ReconciliationMatrixTable",
                            "singleVisual": {
                                "visualType": "tableEx",
                                "projections": {
                                    "Values": [
                                        {"queryRef": "DataQualityReconciliation.table_name"},
                                        {"queryRef": "DataQualityReconciliation.raw_ingested"},
                                        {"queryRef": "DataQualityReconciliation.exact_duplicates_dropped"},
                                        {"queryRef": "DataQualityReconciliation.quarantined_rejected"},
                                        {"queryRef": "DataQualityReconciliation.merged_deduplicated"},
                                        {"queryRef": "DataQualityReconciliation.clean_loaded"},
                                        {"queryRef": "DataQualityReconciliation.preservation_rate"},
                                        {"queryRef": "DataQualityReconciliation.reconciliation_status"}
                                    ]
                                }
                            }
                        })
                    },
                    {
                        "x": 815, "y": 175, "width": 445, "height": 525,
                        "config": json.dumps({
                            "name": "ChartEntityOutcomes",
                            "singleVisual": {
                                "visualType": "clusteredBarChart",
                                "projections": {
                                    "Category": [{"queryRef": "DataQualityReconciliation.table_name"}],
                                    "Y": [{"queryRef": "DataQualityReconciliation.Total Clean Records"}]
                                }
                            }
                        })
                    }
                ]
            }
        ]
    }
    # 4b. Sync TMDL Date table if TMDL directory exists
    date_tmdl = MODEL_DIR / "definition" / "tables" / "Date.tmdl"
    if date_tmdl.parent.exists():
        date_tmdl_content = """/// Marked calendar date dimension
table Date
\tlineageTag: 922d2cd5-ce9c-459b-9ff1-339549ec03e6

\tcolumn date_key
\t\tdataType: dateTime
\t\tformatString: yyyy-mm-dd
\t\tlineageTag: fdba0ce3-c440-40d3-bfb5-740a962f8ced
\t\tsummarizeBy: none
\t\tsourceColumn: date_key

\t\tannotation UnderlyingDateTimeDataType = Date
\t\tannotation SummarizationSetBy = Automatic

\tcolumn year
\t\tdataType: int64
\t\tlineageTag: 0ab98c76-c0ef-4ba1-a249-ed627e5e9c29
\t\tsummarizeBy: none
\t\tsourceColumn: year

\t\tannotation SummarizationSetBy = Automatic

\tcolumn quarter
\t\tdataType: int64
\t\tlineageTag: 02d66da4-1497-45cd-bb5e-74d1cbf55815
\t\tsummarizeBy: none
\t\tsourceColumn: quarter

\t\tannotation SummarizationSetBy = Automatic

\tcolumn quarter_name
\t\tdataType: string
\t\tlineageTag: 6b076e68-decd-4e8b-8066-b954d260a7a5
\t\tsourceColumn: quarter_name

\tcolumn month
\t\tdataType: int64
\t\tlineageTag: 9519a974-881f-418f-9e0c-348bf5d5f29b
\t\tsummarizeBy: none
\t\tsourceColumn: month

\t\tannotation SummarizationSetBy = Automatic

\tcolumn month_name
\t\tdataType: string
\t\tlineageTag: a4a9f317-46a1-4c1d-b6d5-6f5a3a393d6b
\t\tsourceColumn: month_name

\tcolumn year_month
\t\tdataType: string
\t\tlineageTag: 775ca94d-555f-4c0c-823d-0f3ec2cc6827
\t\tsummarizeBy: none
\t\tsourceColumn: year_month

\tcolumn day
\t\tdataType: int64
\t\tlineageTag: 04edc1ae-2b25-4495-bfc5-1f969ca6e07b
\t\tsummarizeBy: none
\t\tsourceColumn: day

\t\tannotation SummarizationSetBy = Automatic

\tcolumn day_of_week
\t\tdataType: int64
\t\tlineageTag: 63a26ea9-9569-4126-8fa5-2207d6cec164
\t\tsummarizeBy: none
\t\tsourceColumn: day_of_week

\t\tannotation SummarizationSetBy = Automatic

\tcolumn day_name
\t\tdataType: string
\t\tlineageTag: e3a096c0-44fa-4724-8111-182a725d99dd
\t\tsourceColumn: day_name

\tcolumn is_weekend
\t\tdataType: boolean
\t\tlineageTag: 7e1fc5b4-e0e1-404c-ac72-e4cf08c75bd2
\t\tsummarizeBy: none
\t\tsourceColumn: is_weekend

\t\tannotation SummarizationSetBy = Automatic

\tpartition DatePartition = m
\t\tsource =
\t\t\t\tlet
\t\t\t\t    FolderPath = if Text.EndsWith(DataFolder, "\\") or Text.EndsWith(DataFolder, "/") then DataFolder else DataFolder & "\\",
\t\t\t\t    Source = Csv.Document(File.Contents(FolderPath & "dim_date.csv"), [Delimiter=",", Columns=11, Encoding=65001, QuoteStyle=QuoteStyle.None]),
\t\t\t\t    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
\t\t\t\t    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"date_key", type date}, {"year", Int64.Type}, {"quarter", Int64.Type}, {"quarter_name", type text}, {"month", Int64.Type}, {"month_name", type text}, {"year_month", type text}, {"day", Int64.Type}, {"day_of_week", Int64.Type}, {"day_name", type text}, {"is_weekend", type logical}}, "en-US")
\t\t\t\tin
\t\t\t\t    #"Changed Type"
"""
        with open(date_tmdl, "w", encoding="utf-8") as f:
            f.write(date_tmdl_content)

    # 4c. Sync TMDL DataQualityReconciliation table if TMDL directory exists
    dqr_tmdl = MODEL_DIR / "definition" / "tables" / "DataQualityReconciliation.tmdl"
    if dqr_tmdl.parent.exists():
        dqr_tmdl_content = """/// Pipeline data assurance reconciliation matrix
table DataQualityReconciliation
\tlineageTag: f36f448b-ae6e-499c-9d24-83b47cc5cf8e

\tmeasure 'Total Raw Records' = SUM(DataQualityReconciliation[raw_ingested])
\t\tformatString: #,0
\t\tlineageTag: 97d051d1-6a71-4f16-af12-8bd917950bc4

\tmeasure 'Total Clean Records' = SUM(DataQualityReconciliation[clean_loaded])
\t\tformatString: #,0
\t\tlineageTag: 81dc7846-d182-4cd9-98fe-a0947ca576f1

\tmeasure 'Total Duplicate Records' = SUM(DataQualityReconciliation[exact_duplicates_dropped])
\t\tformatString: #,0
\t\tlineageTag: a7b1c3d5-8e9f-4104-b362-b46ec4192680

\tmeasure 'Total Quarantined Records' = SUM(DataQualityReconciliation[quarantined_rejected])
\t\tformatString: #,0
\t\tlineageTag: b8c2d4e6-9f0a-4909-a27f-91c6b27b6fee

\tmeasure 'Overall Preservation Rate %' = DIVIDE([Total Clean Records], [Total Raw Records])
\t\tformatString: 0.0%
\t\tlineageTag: 72d252c0-60fe-4b7a-bbe5-728a7cd331f8

\tcolumn table_name
\t\tdataType: string
\t\tlineageTag: 08c1a63f-852d-4882-b761-004819bca863
\t\tsourceColumn: table_name

\tcolumn raw_ingested
\t\tdataType: int64
\t\tformatString: #,0
\t\tlineageTag: 35ae13f9-fd1f-4c76-89a8-ff395438e90b
\t\tsummarizeBy: sum
\t\tsourceColumn: raw_ingested

\t\tannotation SummarizationSetBy = Automatic

\tcolumn exact_duplicates_dropped
\t\tdataType: int64
\t\tformatString: #,0
\t\tlineageTag: 0ee2acd9-939c-4104-b362-b46ec4192680
\t\tsummarizeBy: sum
\t\tsourceColumn: exact_duplicates_dropped

\t\tannotation SummarizationSetBy = Automatic

\tcolumn quarantined_rejected
\t\tdataType: int64
\t\tformatString: #,0
\t\tlineageTag: 4879b1cf-771a-4909-a27f-91c6b27b6fee
\t\tsummarizeBy: sum
\t\tsourceColumn: quarantined_rejected

\t\tannotation SummarizationSetBy = Automatic

\tcolumn merged_deduplicated
\t\tdataType: int64
\t\tformatString: #,0
\t\tlineageTag: 20feace9-c416-4285-a64a-c52340ea75fb
\t\tsummarizeBy: sum
\t\tsourceColumn: merged_deduplicated

\t\tannotation SummarizationSetBy = Automatic

\tcolumn clean_loaded
\t\tdataType: int64
\t\tformatString: #,0
\t\tlineageTag: 796ba9f3-6d11-4cad-b835-35d9db6a337a
\t\tsummarizeBy: sum
\t\tsourceColumn: clean_loaded

\t\tannotation SummarizationSetBy = Automatic

\tcolumn reconciliation_status
\t\tdataType: string
\t\tlineageTag: bfbcb475-95bb-42d2-88e7-406b5fbce379
\t\tsourceColumn: reconciliation_status

\tcolumn preservation_rate
\t\tdataType: double
\t\tformatString: 0.0%
\t\tlineageTag: 37d04086-1a32-4c86-8271-37782fa03fce
\t\tsummarizeBy: none
\t\tsourceColumn: preservation_rate

\t\tannotation SummarizationSetBy = Automatic

\tpartition ReconciliationPartition = m
\t\tsource =
\t\t\t\tlet
\t\t\t\t    FolderPath = if Text.EndsWith(DataFolder, "\\") or Text.EndsWith(DataFolder, "/") then DataFolder else DataFolder & "\\",
\t\t\t\t    Source = Csv.Document(File.Contents(FolderPath & "data_assurance_reconciliation.csv"), [Delimiter=",", Columns=8, Encoding=65001, QuoteStyle=QuoteStyle.None]),
\t\t\t\t    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
\t\t\t\t    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{"table_name", type text}, {"raw_ingested", Int64.Type}, {"exact_duplicates_dropped", Int64.Type}, {"quarantined_rejected", Int64.Type}, {"merged_deduplicated", Int64.Type}, {"clean_loaded", Int64.Type}, {"reconciliation_status", type text}, {"preservation_rate", type number}}, "en-US")
\t\t\t\tin
\t\t\t\t    #"Changed Type"
"""
        with open(dqr_tmdl, "w", encoding="utf-8") as f:
            f.write(dqr_tmdl_content)

    # 5. Full report.json with prototypeQuery & projections for standard Power BI Desktop
    try:
        from scripts.generate_report_json import build_full_report_json
        build_full_report_json()
    except Exception as e:
        print(f"Notice: report.json generator skipped: {e}")

    # 6. PBIR Visual Containers (definition/pages/*/visuals/*/visual.json)
    try:
        from scripts.generate_pbir_visuals import build_all_visuals
        build_all_visuals()
    except Exception as e:
        print(f"Notice: PBIR visual generator skipped: {e}")

    print("Successfully built PBIP project structure:")
    print(f"  {POWERBI_DIR / 'InsightFlow.pbip'}")
    print(f"  {REPORT_DIR / 'definition.pbir'}")
    print(f"  {MODEL_DIR / 'definition.pbism'}")
    print(f"  {MODEL_DIR / 'model.bim'}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate modern Power BI Project (PBIP) structure")
    parser.add_argument("--clean-cache", action="store_true", help="Purge Analysis Services cache.abf and localSettings.json")
    args = parser.parse_args()
    build_pbip(clean_cache=args.clean_cache)
