"""Generate all 27 visual.json files in definition/pages/ with full PBIR queryState bindings."""

import json
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORT_DIR = PROJECT_ROOT / "powerbi" / "InsightFlow.Report"
PAGES_DIR = REPORT_DIR / "definition" / "pages"


def make_textbox(name, title_text, x, y, width, height, font_size="18pt"):
    return {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": 0, "height": height, "width": width, "tabOrder": 0},
        "visual": {
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
                                                "fontFamily": "Segoe UI Semibold",
                                                "fontSize": font_size,
                                                "color": "#111827",
                                            },
                                        }
                                    ],
                                    "horizontalTextAlignment": "left",
                                }
                            ]
                        }
                    }
                ]
            },
        },
    }


def make_card(name, entity, property_name, x, y, width, height, title=None, z=1000):
    vis = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": z, "height": height, "width": width, "tabOrder": z},
        "visual": {
            "visualType": "cardVisual",
            "query": {
                "queryState": {
                    "Data": {
                        "projections": [
                            {
                                "field": {
                                    "Measure": {
                                        "Expression": {"SourceRef": {"Entity": entity}},
                                        "Property": property_name,
                                    }
                                },
                                "queryRef": f"{entity}.{property_name}",
                            }
                        ]
                    }
                }
            },
        },
    }
    if title:
        vis["visual"]["visualContainerObjects"] = {
            "title": [
                {
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
                    }
                }
            ]
        }
    return vis


def make_chart(
    name,
    visual_type,
    category_entity,
    category_prop,
    y_entity,
    y_prop,
    x,
    y,
    width,
    height,
    is_y_measure=True,
    title=None,
    z=2000,
):
    y_field_type = "Measure" if is_y_measure else "Column"
    pbir_type = "clusteredBarChart" if visual_type == "barChart" else visual_type
    vis = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": z, "height": height, "width": width, "tabOrder": z},
        "visual": {
            "visualType": pbir_type,
            "query": {
                "queryState": {
                    "Category": {
                        "projections": [
                            {
                                "field": {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Entity": category_entity}},
                                        "Property": category_prop,
                                    }
                                },
                                "queryRef": f"{category_entity}.{category_prop}",
                            }
                        ]
                    },
                    "Y": {
                        "projections": [
                            {
                                "field": {
                                    y_field_type: {
                                        "Expression": {"SourceRef": {"Entity": y_entity}},
                                        "Property": y_prop,
                                    }
                                },
                                "queryRef": f"{y_entity}.{y_prop}",
                            }
                        ]
                    },
                }
            },
        },
    }
    if title:
        vis["visual"]["visualContainerObjects"] = {
            "title": [
                {
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
                    }
                }
            ]
        }
    return vis


def make_scatter(
    name,
    cat_entity,
    cat_prop,
    x_entity,
    x_prop,
    y_entity,
    y_prop,
    x,
    y,
    width,
    height,
    title=None,
    z=2000,
):
    vis = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": z, "height": height, "width": width, "tabOrder": z},
        "visual": {
            "visualType": "scatterChart",
            "query": {
                "queryState": {
                    "Category": {
                        "projections": [
                            {
                                "field": {
                                    "Column": {
                                        "Expression": {"SourceRef": {"Entity": cat_entity}},
                                        "Property": cat_prop,
                                    }
                                },
                                "queryRef": f"{cat_entity}.{cat_prop}",
                            }
                        ]
                    },
                    "X": {
                        "projections": [
                            {
                                "field": {
                                    "Measure": {
                                        "Expression": {"SourceRef": {"Entity": x_entity}},
                                        "Property": x_prop,
                                    }
                                },
                                "queryRef": f"{x_entity}.{x_prop}",
                            }
                        ]
                    },
                    "Y": {
                        "projections": [
                            {
                                "field": {
                                    "Measure": {
                                        "Expression": {"SourceRef": {"Entity": y_entity}},
                                        "Property": y_prop,
                                    }
                                },
                                "queryRef": f"{y_entity}.{y_prop}",
                            }
                        ]
                    },
                }
            },
        },
    }
    if title:
        vis["visual"]["visualContainerObjects"] = {
            "title": [
                {
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
                    }
                }
            ]
        }
    return vis


def make_table(name, columns_and_measures, x, y, width, height, title=None, z=2000):
    projections = []
    for item in columns_and_measures:
        entity, prop, is_measure = item
        f_type = "Measure" if is_measure else "Column"
        projections.append(
            {
                "field": {
                    f_type: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}
                },
                "queryRef": f"{entity}.{prop}",
            }
        )
    vis = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json",
        "name": name,
        "position": {"x": x, "y": y, "z": z, "height": height, "width": width, "tabOrder": z},
        "visual": {
            "visualType": "tableEx",
            "query": {"queryState": {"Values": {"projections": projections}}},
        },
    }
    if title:
        vis["visual"]["visualContainerObjects"] = {
            "title": [
                {
                    "properties": {
                        "show": {"expr": {"Literal": {"Value": "true"}}},
                        "text": {"expr": {"Literal": {"Value": f"'{title}'"}}},
                    }
                }
            ]
        }
    return vis


def write_visual(page_name, visual_dict):
    vis_dir = PAGES_DIR / page_name / "visuals" / visual_dict["name"]
    vis_dir.mkdir(parents=True, exist_ok=True)
    out_file = vis_dir / "visual.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(visual_dict, f, indent=2)
    return out_file


def build_all_visuals():
    written = []

    # Page 1: Executive Profitability
    p1 = "ReportSection_ExecProfitability"
    written.append(
        write_visual(
            p1, make_textbox("PageHeader", "Executive Profitability Overview", 20, 20, 1240, 50)
        )
    )
    written.append(
        write_visual(
            p1, make_card("CardRevenue", "Sales", "Revenue", 20, 80, 230, 110, "Net Revenue")
        )
    )
    written.append(
        write_visual(
            p1,
            make_card(
                "CardGrossProfit", "Sales", "Gross Profit", 270, 80, 230, 110, "Gross Profit"
            ),
        )
    )
    written.append(
        write_visual(
            p1,
            make_card(
                "CardGrossMargin", "Sales", "Gross Margin %", 520, 80, 230, 110, "Gross Margin %"
            ),
        )
    )
    written.append(
        write_visual(
            p1, make_card("CardOrders", "Sales", "Orders", 770, 80, 230, 110, "Completed Orders")
        )
    )
    written.append(
        write_visual(
            p1,
            make_card(
                "CardAOV", "Sales", "Average Order Value", 1020, 80, 240, 110, "Average Order Value"
            ),
        )
    )
    written.append(
        write_visual(
            p1,
            make_chart(
                "MonthlyRevenueTrend",
                "lineChart",
                "Date",
                "year_month",
                "Sales",
                "Revenue",
                20,
                210,
                780,
                480,
                is_y_measure=True,
                title="Monthly Net Revenue Trend",
            ),
        )
    )
    written.append(
        write_visual(
            p1,
            make_chart(
                "CategoryRevenueBreakdown",
                "barChart",
                "Product",
                "category_name",
                "Sales",
                "Revenue",
                820,
                210,
                440,
                480,
                is_y_measure=True,
                title="Net Revenue by Product Category",
            ),
        )
    )

    # Page 2: Margin Investigation
    p2 = "ReportSection_MarginInvestigation"
    written.append(
        write_visual(
            p2,
            make_textbox(
                "HeaderMargin",
                "Product Margin Investigation & Flagship Elasticity",
                20,
                20,
                1240,
                50,
            ),
        )
    )
    written.append(
        write_visual(
            p2,
            make_card(
                "CardBasmatiRev",
                "Sales",
                "Basmati Rice Net Revenue",
                20,
                80,
                290,
                110,
                "Basmati Rice Net Revenue (P0010)",
            ),
        )
    )
    written.append(
        write_visual(
            p2,
            make_card(
                "CardBasmatiGP",
                "Sales",
                "Basmati Rice Gross Profit",
                330,
                80,
                290,
                110,
                "Basmati Rice Gross Profit",
            ),
        )
    )
    written.append(
        write_visual(
            p2,
            make_card(
                "CardBasmatiMargin",
                "Sales",
                "Basmati Rice Margin %",
                640,
                80,
                290,
                110,
                "Basmati Rice Gross Margin %",
            ),
        )
    )
    written.append(
        write_visual(
            p2,
            make_card(
                "CardBasmatiTolerance",
                "Sales",
                "Basmati Break Even Volume Decline %",
                950,
                80,
                310,
                110,
                "Volume Decline Tolerance (+3% Price)",
            ),
        )
    )
    written.append(
        write_visual(
            p2,
            make_scatter(
                "MarginScatter",
                "Product",
                "product_name",
                "Sales",
                "Revenue",
                "Sales",
                "Gross Profit",
                20,
                210,
                780,
                480,
                title="Product Net Revenue vs Gross Profit",
            ),
        )
    )
    written.append(
        write_visual(
            p2,
            make_chart(
                "SupplierMarginRanking",
                "barChart",
                "Product",
                "supplier_name",
                "Sales",
                "Gross Margin %",
                820,
                210,
                440,
                480,
                is_y_measure=True,
                title="Gross Margin % by Supplier",
            ),
        )
    )

    # Page 3: Inventory Decisions
    p3 = "ReportSection_InventoryDecisions"
    written.append(
        write_visual(
            p3,
            make_textbox(
                "HeaderInventory",
                "Inventory Intelligence & Capital Replenishment",
                20,
                20,
                1240,
                50,
            ),
        )
    )
    written.append(
        write_visual(
            p3,
            make_card(
                "CardStockVal", "Inventory", "Stock Value", 20, 80, 230, 110, "Total Stock Value"
            ),
        )
    )
    written.append(
        write_visual(
            p3,
            make_card(
                "CardStockouts",
                "Inventory",
                "Stockout Positions",
                270,
                80,
                230,
                110,
                "Out of Stock Positions",
            ),
        )
    )
    written.append(
        write_visual(
            p3,
            make_card(
                "CardBelowReorder",
                "Inventory",
                "Positions Below Reorder",
                520,
                80,
                230,
                110,
                "Positions Below Reorder",
            ),
        )
    )
    written.append(
        write_visual(
            p3,
            make_card(
                "CardReplenishCost",
                "Inventory",
                "Replenishment Cost Estimate",
                770,
                80,
                230,
                110,
                "Replenishment Working Capital",
            ),
        )
    )
    written.append(
        write_visual(
            p3,
            make_card(
                "CardStockGapRetail",
                "Inventory",
                "Stock Gap Retail Valuation",
                1020,
                80,
                240,
                110,
                "Stock Gap Retail Valuation",
            ),
        )
    )
    written.append(
        write_visual(
            p3,
            make_chart(
                "StockStatusMix",
                "pieChart",
                "Inventory",
                "stock_status",
                "Inventory",
                "Stock Positions",
                20,
                210,
                580,
                480,
                is_y_measure=True,
                title="Stock Positions by Health Status",
            ),
        )
    )
    written.append(
        write_visual(
            p3,
            make_table(
                "ReplenishmentQueueTable",
                [
                    ("Product", "product_name", False),
                    ("Location", "location_name", False),
                    ("Inventory", "quantity_on_hand", False),
                    ("Inventory", "reorder_level", False),
                    ("Inventory", "replenishment_quantity_required", False),
                    ("Inventory", "replenishment_cost_estimate", False),
                ],
                620,
                210,
                640,
                480,
                title="Priority Stock Replenishment Queue",
            ),
        )
    )

    # Page 4: Data Integrity & Pipeline Assurance
    p4 = "ReportSection_DataIntegrity"
    written.append(
        write_visual(
            p4,
            make_textbox(
                "HeaderIntegrity",
                "Data Pipeline Assurance & Conservation Reconciliation Matrix",
                20,
                20,
                1240,
                50,
            ),
        )
    )
    written.append(
        write_visual(
            p4,
            make_card(
                "CardTotalRaw",
                "DataQualityReconciliation",
                "Total Raw Records",
                20,
                80,
                380,
                110,
                "Raw Records Ingested",
            ),
        )
    )
    written.append(
        write_visual(
            p4,
            make_card(
                "CardTotalClean",
                "DataQualityReconciliation",
                "Total Clean Records",
                430,
                80,
                380,
                110,
                "Clean Records Loaded",
            ),
        )
    )
    written.append(
        write_visual(
            p4,
            make_card(
                "CardPreservationRate",
                "DataQualityReconciliation",
                "Overall Preservation Rate %",
                840,
                80,
                420,
                110,
                "Data Preservation Rate %",
            ),
        )
    )
    written.append(
        write_visual(
            p4,
            make_table(
                "ReconciliationMatrixTable",
                [
                    ("DataQualityReconciliation", "table_name", False),
                    ("DataQualityReconciliation", "raw_ingested", False),
                    ("DataQualityReconciliation", "exact_duplicates_dropped", False),
                    ("DataQualityReconciliation", "quarantined_rejected", False),
                    ("DataQualityReconciliation", "merged_deduplicated", False),
                    ("DataQualityReconciliation", "clean_loaded", False),
                    ("DataQualityReconciliation", "preservation_rate", False),
                    ("DataQualityReconciliation", "reconciliation_status", False),
                ],
                20,
                210,
                1240,
                480,
                title="End-to-End Pipeline Reconciliation Matrix",
            ),
        )
    )

    print(f"Successfully generated {len(written)} PBIR visual.json files!")
    return written


if __name__ == "__main__":
    build_all_visuals()
