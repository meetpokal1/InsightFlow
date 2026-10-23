# InsightFlow Power BI — Blank Visuals Root-Cause Investigation Report

**Investigation Date:** October 23, 2026  
**Project:** InsightFlow Retail Analytics Decision-Support Product  
**Path:** `powerbi/`  
**Power BI Project:** `powerbi/InsightFlow.pbip`  
**Git Branch:** `feature/sprint1-analytics-upgrade`  

---

## 1. Executive Summary & Root-Cause Diagnosis

### The Problem
Power BI Desktop version 2.159.883.0 (October 2026) opens `InsightFlow.pbip` without schema errors, and all seven tables refresh successfully from the CSV data extracts in `powerbi/data/`. However, upon viewing the report canvas, all visuals across the four pages appeared completely blank/gray, displaying no numbers, charts, tables, or error dialogs.

### The Root Cause
1. **PBIR Format Migration Gap**:
   - Modern Power BI Desktop versions serialize Power BI Projects (`.pbip`) using the **Microsoft Fabric Power BI Enhanced Report Format (PBIR)**, decomposing report definitions into `definition/pages/<PageName>/visuals/<VisualName>/visual.json`.
   - Previously, `scripts/build_powerbi_pbip.py` emitted a legacy flat `report.json` containing visual containers with simplified `singleVisual` blocks:
     ```json
     "singleVisual": {
       "visualType": "card",
       "projections": {"Values": [{"queryRef": "Sales.Revenue"}]}
     }
     ```
   - When Power BI Desktop opened the project, its internal migration engine upgraded `report.json` into the `definition/pages/` folder hierarchy.
   - However, because the legacy `singleVisual` blocks lacked the complete Power BI query AST (`prototypeQuery` with `From`, `Select`, `SourceRef`), the migration parser successfully extracted the container bounds and `"visualType"` (e.g. `card`, `barChart`, `lineChart`, `tableEx`), but **silently dropped all data field projections**.
2. **Missing `queryState` Data Bindings in `visual.json`**:
   - Examination of the migrated `visual.json` files revealed that every single visual container was saved with only:
     ```json
     {
       "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json",
       "name": "CardRevenue",
       "position": { ... },
       "visual": {
         "visualType": "card"
       }
     }
     ```
   - There was **no `query` object**, **no `queryState`**, and **zero data-role projections**.
   - Power BI Desktop rendered the container boxes at their specified coordinates, but with no measures or columns bound, each visual was rendered as a blank empty container.
3. **Missing Textbox Content Structure**:
   - Header textboxes (`PageHeader`, `HeaderMargin`, `HeaderInventory`, `HeaderIntegrity`) lacked the PBIR-compliant `visual.objects.general[0].properties.paragraphs[0].textRuns` structure, rendering header banners empty.

---

## 2. Investigation Findings

### Investigation A — PBIP Directory & File Hierarchy
- `definition.pbir` correctly references `../InsightFlow.SemanticModel`.
- `definition/pages/pages.json` correctly defines the 4 active report pages in order:
  1. `ReportSection_ExecProfitability` ("Executive Profitability")
  2. `ReportSection_MarginInvestigation` ("Margin Investigation")
  3. `ReportSection_InventoryDecisions` ("Inventory Decisions")
  4. `ReportSection_DataIntegrity` ("Data Integrity & Pipeline Assurance")
- Each page folder contains `page.json` and a `visuals/` directory containing all intended visual containers.

### Investigation B — Visual Binding Cross-Reference Audit
An automated audit (`scripts/audit_visual_bindings.py`) cross-referenced all 28 visual containers against the semantic model (`definition/tables/*.tmdl`):
- **Pages Audited:** 4 pages.
- **Visuals Audited:** 28 visual containers.
- **Missing Field/Measure References:** **0**.
- **Invalid Projections:** **0**.
- **Result:** Every referenced measure and column exists with exact case and spelling in the model.

### Investigation C — Model & Data Verification
Row counts and KPI checkpoints were independently computed against the extract files in `powerbi/data/`:

| Dataset / Table | Actual Disk Extract | Intended Semantic Role | Status |
|---|---|---|---|
| `Sales` | 34,007 rows, 12 cols | Line-level completed order transactions | Verified |
| `Inventory` | 449 rows, 21 cols | Product-location stock snapshot as of 30 Sept 2026 | Verified |
| `Product` | 60 rows, 11 cols | Product catalog dimension | Verified |
| `Customer` | 800 rows, 8 cols | Customer dimension with RFM segmentation | Verified |
| `Location` | 8 rows, 6 cols | Store and fulfillment locations | Verified |
| `Date` | 1,004 rows, 11 cols | Calendar dimension (2024-01-01 to 2026-09-30) | Verified |
| `DataQualityReconciliation` | 8 rows, 8 cols | Pipeline data assurance reconciliation matrix | Verified |

*Note on Row Counts:* The 34,007 rows in `Sales` represent all line items belonging to the **7,878 distinct completed customer orders** (18,349 was an estimated order-count figure previously cited, whereas the actual completed order count is exactly 7,878 with 34,007 line items).

#### Unfiltered KPI Checkpoint Verification:
- **Net Revenue:** ₹209,034,798.31 (Matches exact benchmark: ₹209.03M)
- **Gross Profit:** ₹42,355,329.09 (Matches exact benchmark: ₹42.36M)
- **Gross Margin %:** 20.26% (Matches exact benchmark: 20.26%)
- **Completed Orders:** 7,878 distinct orders
- **Average Order Value (AOV):** ₹26,534.00 (Matches exact benchmark: ₹26,534)
- **Active Customers:** 780 distinct buying customers (out of 800 registered)
- **Items Needing Action:** 92 positions (Out of stock: 39, Stock-out risk: 39, Low stock: 14)
- **Stock Value:** ₹22,488,675.00 (₹22.49M)
- **Replenishment Cost Estimate:** ₹966,456.00 (₹9.66 L working capital required)
- **Stock Gap Retail Valuation:** ₹1,341,250.00 (₹13.41 L catalog valuation)

#### Relationship Integrity:
All 6 relationships in `definition/relationships.tmdl` were validated:
- `Sales[product_id]` $\rightarrow$ `Product[product_id]` (1:many, active, 0 orphans)
- `Sales[customer_id]` $\rightarrow$ `Customer[customer_id]` (1:many, active, 0 orphans)
- `Sales[location_id]` $\rightarrow$ `Location[location_id]` (1:many, active, 0 orphans)
- `Sales[order_date]` $\rightarrow$ `Date[date_key]` (1:many, active, 0 orphans)
- `Inventory[product_id]` $\rightarrow$ `Product[product_id]` (1:many, active, 0 orphans)
- `Inventory[location_id]` $\rightarrow$ `Location[location_id]` (1:many, active, 0 orphans)

---

## 3. Changes Implemented

1. **Created Dedicated PBIR Visual Generator ([generate_pbir_visuals.py](file:///C:/Users/Meet%20Pokal/.gemini/antigravity/scratch/InsightFlow/scripts/generate_pbir_visuals.py))**:
   - Implemented standard Microsoft Fabric PBIR visual schema generation targeting schema `visualContainer/2.14.0/schema.json`.
   - Wired `visual.query.queryState` with exact data roles:
     - `card`: `"Values"` data role bound to target DAX measures.
     - `lineChart`: `"Category"` bound to `Date.year_month`, `"Y"` bound to `Sales.Revenue`.
     - `barChart`: `"Category"` bound to dimension attributes, `"Y"` bound to measures.
     - `scatterChart`: `"Category"` bound to `Product.product_name`, `"X"` to `Sales.Revenue`, `"Y"` to `Sales.Gross Profit`.
     - `pieChart`: `"Category"` bound to `Inventory.stock_status`, `"Y"` to `Inventory.Stock Positions`.
     - `tableEx`: `"Values"` role projecting all required column and measure fields.
     - `textbox`: Formatted paragraphs, font styling (`Segoe UI Semibold`), and textRun values.
   - Wired container title objects via `visual.visualContainerObjects.title` with PBIR-standard single-quoted string literals (`"'Title Text'"`).

2. **Updated Project Builder ([build_powerbi_pbip.py](file:///C:/Users/Meet%20Pokal/.gemini/antigravity/scratch/InsightFlow/scripts/build_powerbi_pbip.py))**:
   - Integrated `build_all_visuals()` into the build process so future PBIP builds consistently generate valid PBIR visual containers alongside `model.bim` and `report.json`.

3. **Added PBIR Visual Binding Validation Tests ([test_powerbi_deliverable.py](file:///C:/Users/Meet%20Pokal/.gemini/antigravity/scratch/InsightFlow/tests/test_powerbi_deliverable.py))**:
   - Added `test_pbir_visual_containers_bindings_and_data_roles()` which iterates through all 28 `visual.json` files, verifying that:
     - No visual has an empty `queryState`.
     - All projected `Measure` and `Column` entities and properties resolve to existing fields in the model.
     - All textboxes contain valid, non-empty textRun values.

4. **Created Automated Binding Audit Tool ([audit_visual_bindings.py](file:///C:/Users/Meet%20Pokal/.gemini/antigravity/scratch/InsightFlow/scripts/audit_visual_bindings.py))**:
   - Reports detailed visual inventory, data roles, and validation results across all 4 pages.

---

## 4. Test Results

- **PBIP Deliverable Tests:**
  `pytest tests/test_powerbi_deliverable.py -v` $\rightarrow$ **7 passed in 0.11s, 0 failed**.
- **Audit Tool:**
  `python scripts/audit_visual_bindings.py` $\rightarrow$ **28 visuals audited, 0 unresolved references**.
- **Full Test Suite:**
  `pytest tests/ -v` $\rightarrow$ **155 passed, 69 skipped in 26.88s, 0 failed**.

---

## 5. Remaining Risks & Verification Status

- **Programmatic Verification:** **PASS (100%)**. Model integrity, relationships, row counts, DAX measures, CSV data paths, and PBIR queryState projections are programmatically verified.
- **Desktop Visual Rendering:** **PENDING MANUAL CONFIRMATION**. Because Power BI Desktop is an interactive Windows GUI application, direct programmatic inspection cannot observe the final rendered pixels on screen. In accordance with the project safety rules, the report is classified as **Programmatically Verified / Pending Final User Desktop Refresh**.
