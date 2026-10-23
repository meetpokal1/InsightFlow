"""Generate standard Power BI report.json with full prototypeQuery and projection bindings.

Compatible with Power BI Desktop out-of-the-box (no preview features required).
"""

import json
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORT_FILE = PROJECT_ROOT / "powerbi" / "InsightFlow.Report" / "report.json"


def get_alias(entity):
    mapping = {
        "Sales": "s",
        "Inventory": "i",
        "Product": "p",
        "Customer": "c",
        "Location": "l",
        "Date": "d",
        "DataQualityReconciliation": "r"
    }
    return mapping.get(entity, entity[0].lower())


def build_select_item(entity, prop, is_measure):
    alias = get_alias(entity)
    field_kind = "Measure" if is_measure else "Column"
    return {
        field_kind: {
            "Expression": {
                "SourceRef": {
                    "Source": alias
                }
            },
            "Property": prop
        },
        "Name": f"{entity}.{prop}"
    }


def make_card_container(name, entity, prop, x, y, width, height, title, z=1000):
    alias = get_alias(entity)
    cfg = {
        "name": name,
        "layouts": [
            {
                "id": 0,
                "position": {
                    "x": x,
                    "y": y,
                    "z": z,
                    "width": width,
                    "height": height
                }
            }
        ],
        "singleVisual": {
            "visualType": "card",
            "projections": {
                "Values": [
                    {
                        "queryRef": f"{entity}.{prop}"
                    }
                ]
            },
            "prototypeQuery": {
                "Version": 2,
                "From": [
                    {
                        "Name": alias,
                        "Entity": entity,
                        "Type": 0
                    }
                ],
                "Select": [
                    build_select_item(entity, prop, is_measure=True)
                ]
            },
            "objects": {
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {"expr": {"Literal": {"Value": f"'{title}'"}}}
                        }
                    }
                ]
            }
        }
    }
    return {
        "x": x,
        "y": y,
        "z": z,
        "width": width,
        "height": height,
        "config": json.dumps(cfg)
    }


def make_chart_container(name, visual_type, cat_entity, cat_prop, y_entity, y_prop, x, y, width, height, title, is_y_measure=True, z=2000, order_by_cat=False):
    cat_alias = get_alias(cat_entity)
    y_alias = get_alias(y_entity)
    from_list = [{"Name": cat_alias, "Entity": cat_entity, "Type": 0}]
    if y_alias != cat_alias:
        from_list.append({"Name": y_alias, "Entity": y_entity, "Type": 0})

    proto = {
        "Version": 2,
        "From": from_list,
        "Select": [
            build_select_item(cat_entity, cat_prop, is_measure=False),
            build_select_item(y_entity, y_prop, is_measure=is_y_measure)
        ]
    }
    if order_by_cat:
        proto["OrderBy"] = [
            {
                "Direction": 1,
                "Expression": {
                    "Column": {
                        "Expression": {
                            "SourceRef": {
                                "Source": cat_alias
                            }
                        },
                        "Property": cat_prop
                    }
                }
            }
        ]

    cfg = {
        "name": name,
        "layouts": [
            {
                "id": 0,
                "position": {
                    "x": x,
                    "y": y,
                    "z": z,
                    "width": width,
                    "height": height
                }
            }
        ],
        "singleVisual": {
            "visualType": visual_type,
            "projections": {
                "Category": [
                    {
                        "queryRef": f"{cat_entity}.{cat_prop}",
                        "active": True
                    }
                ],
                "Y": [
                    {
                        "queryRef": f"{y_entity}.{y_prop}"
                    }
                ]
            },
            "prototypeQuery": proto,
            "objects": {
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {"expr": {"Literal": {"Value": f"'{title}'"}}}
                        }
                    }
                ]
            }
        }
    }
    return {
        "x": x,
        "y": y,
        "z": z,
        "width": width,
        "height": height,
        "config": json.dumps(cfg)
    }


def make_scatter_container(name, det_entity, det_prop, x_entity, x_prop, y_entity, y_prop, x, y, width, height, title, z=2000):
    det_alias = get_alias(det_entity)
    x_alias = get_alias(x_entity)
    y_alias = get_alias(y_entity)
    entities = {det_entity: det_alias, x_entity: x_alias, y_entity: y_alias}
    from_list = [{"Name": alias, "Entity": ent, "Type": 0} for ent, alias in entities.items()]

    cfg = {
        "name": name,
        "layouts": [
            {
                "id": 0,
                "position": {
                    "x": x,
                    "y": y,
                    "z": z,
                    "width": width,
                    "height": height
                }
            }
        ],
        "singleVisual": {
            "visualType": "scatterChart",
            "projections": {
                "Details": [
                    {
                        "queryRef": f"{det_entity}.{det_prop}"
                    }
                ],
                "X": [
                    {
                        "queryRef": f"{x_entity}.{x_prop}"
                    }
                ],
                "Y": [
                    {
                        "queryRef": f"{y_entity}.{y_prop}"
                    }
                ]
            },
            "prototypeQuery": {
                "Version": 2,
                "From": from_list,
                "Select": [
                    build_select_item(det_entity, det_prop, is_measure=False),
                    build_select_item(x_entity, x_prop, is_measure=True),
                    build_select_item(y_entity, y_prop, is_measure=True)
                ]
            },
            "objects": {
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {"expr": {"Literal": {"Value": f"'{title}'"}}}
                        }
                    }
                ]
            }
        }
    }
    return {
        "x": x,
        "y": y,
        "z": z,
        "width": width,
        "height": height,
        "config": json.dumps(cfg)
    }


def make_table_container(name, cols_and_measures, x, y, width, height, title, z=2000):
    from_dict = {}
    projections = []
    select_items = []
    for ent, prop, is_m in cols_and_measures:
        alias = get_alias(ent)
        from_dict[ent] = alias
        projections.append({"queryRef": f"{ent}.{prop}"})
        select_items.append(build_select_item(ent, prop, is_m))

    from_list = [{"Name": alias, "Entity": ent, "Type": 0} for ent, alias in from_dict.items()]

    cfg = {
        "name": name,
        "layouts": [
            {
                "id": 0,
                "position": {
                    "x": x,
                    "y": y,
                    "z": z,
                    "width": width,
                    "height": height
                }
            }
        ],
        "singleVisual": {
            "visualType": "tableEx",
            "projections": {
                "Values": projections
            },
            "prototypeQuery": {
                "Version": 2,
                "From": from_list,
                "Select": select_items
            },
            "objects": {
                "title": [
                    {
                        "properties": {
                            "show": {"expr": {"Literal": {"Value": "true"}}},
                            "text": {"expr": {"Literal": {"Value": f"'{title}'"}}}
                        }
                    }
                ]
            }
        }
    }
    return {
        "x": x,
        "y": y,
        "z": z,
        "width": width,
        "height": height,
        "config": json.dumps(cfg)
    }


def make_textbox_container(name, title_text, x, y, width, height, z=0):
    cfg = {
        "name": name,
        "layouts": [
            {
                "id": 0,
                "position": {
                    "x": x,
                    "y": y,
                    "z": z,
                    "width": width,
                    "height": height
                }
            }
        ],
        "singleVisual": {
            "visualType": "textbox",
            "objects": {
                "general": [
                    {
                        "properties": {
                            "paragraphs": [
                                {
                                    "textRuns": [
                                        {
                                            "value": title_text,
                                            "textStyle": {
                                                "fontFamily": "'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif",
                                                "fontSize": "16pt",
                                                "color": "#111827"
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ]
            }
        }
    }
    return {
        "x": x,
        "y": y,
        "z": z,
        "width": width,
        "height": height,
        "config": json.dumps(cfg)
    }


def build_full_report_json():
    # Page 1: Executive Profitability
    p1_visuals = [
        make_textbox_container("PageHeader", "Executive Profitability Overview", 20, 20, 1240, 50),
        make_card_container("CardRevenue", "Sales", "Revenue", 20, 80, 230, 110, "Net Revenue"),
        make_card_container("CardGrossProfit", "Sales", "Gross Profit", 270, 80, 230, 110, "Gross Profit"),
        make_card_container("CardGrossMargin", "Sales", "Gross Margin %", 520, 80, 230, 110, "Gross Margin %"),
        make_card_container("CardOrders", "Sales", "Orders", 770, 80, 230, 110, "Completed Orders"),
        make_card_container("CardAOV", "Sales", "Average Order Value", 1020, 80, 240, 110, "Average Order Value"),
        make_chart_container("MonthlyRevenueTrend", "lineChart", "Date", "year_month", "Sales", "Revenue", 20, 210, 780, 480, "Monthly Net Revenue Trend", is_y_measure=True, order_by_cat=True),
        make_chart_container("CategoryRevenueBreakdown", "barChart", "Product", "category_name", "Sales", "Revenue", 820, 210, 440, 480, "Net Revenue by Product Category", is_y_measure=True),
    ]

    # Page 2: Margin Investigation
    p2_visuals = [
        make_textbox_container("HeaderMargin", "Product Margin Investigation & Flagship Elasticity", 20, 20, 1240, 50),
        make_card_container("CardBasmatiRev", "Sales", "Basmati Rice Net Revenue", 20, 80, 290, 110, "Basmati Rice Net Revenue (P0010)"),
        make_card_container("CardBasmatiGP", "Sales", "Basmati Rice Gross Profit", 330, 80, 290, 110, "Basmati Rice Gross Profit"),
        make_card_container("CardBasmatiMargin", "Sales", "Basmati Rice Margin %", 640, 80, 290, 110, "Basmati Rice Gross Margin %"),
        make_card_container("CardBasmatiTolerance", "Sales", "Basmati Break Even Volume Decline %", 950, 80, 310, 110, "Volume Decline Tolerance (+3% Price)"),
        make_scatter_container("MarginScatter", "Product", "product_name", "Sales", "Revenue", "Sales", "Gross Profit", 20, 210, 780, 480, "Product Net Revenue vs Gross Profit"),
        make_chart_container("SupplierMarginRanking", "barChart", "Product", "supplier_name", "Sales", "Gross Margin %", 820, 210, 440, 480, "Gross Margin % by Supplier", is_y_measure=True),
    ]

    # Page 3: Inventory Decisions
    p3_visuals = [
        make_textbox_container("HeaderInventory", "Inventory Intelligence & Capital Replenishment", 20, 20, 1240, 50),
        make_card_container("CardStockVal", "Inventory", "Stock Value", 20, 80, 230, 110, "Total Stock Value"),
        make_card_container("CardStockouts", "Inventory", "Stockout Positions", 270, 80, 230, 110, "Out of Stock Positions"),
        make_card_container("CardBelowReorder", "Inventory", "Positions Below Reorder", 520, 80, 230, 110, "Positions Below Reorder"),
        make_card_container("CardReplenishCost", "Inventory", "Replenishment Cost Estimate", 770, 80, 230, 110, "Replenishment Working Capital"),
        make_card_container("CardStockGapRetail", "Inventory", "Stock Gap Retail Valuation", 1020, 80, 240, 110, "Stock Gap Retail Valuation"),
        make_chart_container("StockStatusMix", "pieChart", "Inventory", "stock_status", "Inventory", "Stock Positions", 20, 210, 580, 480, "Stock Positions by Health Status", is_y_measure=True),
        make_table_container("ReplenishmentQueueTable", [
            ("Product", "product_name", False),
            ("Location", "location_name", False),
            ("Inventory", "quantity_on_hand", False),
            ("Inventory", "reorder_level", False),
            ("Inventory", "replenishment_quantity_required", False),
            ("Inventory", "replenishment_cost_estimate", False),
        ], 620, 210, 640, 480, "Priority Stock Replenishment Queue"),
    ]

    # Page 4: Data Integrity & Pipeline Assurance
    p4_visuals = [
        make_textbox_container("HeaderIntegrity", "Data Pipeline Assurance & Conservation Reconciliation Matrix", 20, 20, 1240, 50),
        make_card_container("CardTotalRaw", "DataQualityReconciliation", "Total Raw Records", 20, 80, 380, 110, "Raw Records Ingested"),
        make_card_container("CardTotalClean", "DataQualityReconciliation", "Total Clean Records", 430, 80, 380, 110, "Clean Records Loaded"),
        make_card_container("CardPreservationRate", "DataQualityReconciliation", "Overall Preservation Rate %", 840, 80, 420, 110, "Data Preservation Rate %"),
        make_table_container("ReconciliationMatrixTable", [
            ("DataQualityReconciliation", "table_name", False),
            ("DataQualityReconciliation", "raw_ingested", False),
            ("DataQualityReconciliation", "exact_duplicates_dropped", False),
            ("DataQualityReconciliation", "quarantined_rejected", False),
            ("DataQualityReconciliation", "merged_deduplicated", False),
            ("DataQualityReconciliation", "clean_loaded", False),
            ("DataQualityReconciliation", "preservation_rate", False),
            ("DataQualityReconciliation", "reconciliation_status", False),
        ], 20, 210, 1240, 480, "End-to-End Pipeline Reconciliation Matrix"),
    ]

    sections = [
        {
            "name": "ReportSection_ExecProfitability",
            "displayName": "Executive Profitability",
            "width": 1280,
            "height": 720,
            "config": json.dumps({"visibility": 0}),
            "visualContainers": p1_visuals
        },
        {
            "name": "ReportSection_MarginInvestigation",
            "displayName": "Margin Investigation",
            "width": 1280,
            "height": 720,
            "config": json.dumps({"visibility": 0}),
            "visualContainers": p2_visuals
        },
        {
            "name": "ReportSection_InventoryDecisions",
            "displayName": "Inventory Decisions",
            "width": 1280,
            "height": 720,
            "config": json.dumps({"visibility": 0}),
            "visualContainers": p3_visuals
        },
        {
            "name": "ReportSection_DataIntegrity",
            "displayName": "Data Integrity & Pipeline Assurance",
            "width": 1280,
            "height": 720,
            "config": json.dumps({"visibility": 0}),
            "visualContainers": p4_visuals
        }
    ]

    report_config = {
        "version": "5.50",
        "themeCollection": {
            "baseTheme": {
                "name": "CY24SU10",
                "reportVersionAtImport": {
                    "visual": "1.8.89",
                    "report": "2.0.89",
                    "page": "1.3.89"
                },
                "type": "SharedResources"
            }
        },
        "activeSectionIndex": 0
    }

    report_data = {
        "config": json.dumps(report_config),
        "layoutOptimization": 0,
        "sections": sections
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2)

    print(f"Successfully generated {REPORT_FILE} with {len(sections)} sections and {sum(len(s['visualContainers']) for s in sections)} visuals!")
    return REPORT_FILE


if __name__ == "__main__":
    build_full_report_json()
