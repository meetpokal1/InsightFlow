# InsightFlow Power BI Deliverable — Release Checklist & Gate

**Audit Date:** October 23, 2026  
**CI Revalidation:** October 24, 2026 — the [PR-head validation run #11](https://github.com/meetpokal1/InsightFlow/actions/runs/40068679173) and [post-merge `main` run #14](https://github.com/meetpokal1/InsightFlow/actions/runs/40069166558) passed. The post-merge run completed database bootstrap and Power BI CSV export, passed 233 tests, and passed Ruff lint/format checks. The source CSV calendar has 2,192 rows (2023-01-01 through 2028-12-31); Power Query filters the model to 730 dates for the current sales period.  
**Project:** InsightFlow Retail Analytics Decision-Support Product  
**Project Directory:** `powerbi/`  
**Power BI Project:** `powerbi/InsightFlow.pbip`  
**Branch:** `feature/sprint1-analytics-upgrade`  

---

## 1. Release Verification Matrix

| Checklist Category | Item Description | Verification Method | Status | Notes |
|---|---|---|---|---|
| **Data Extracts & Refresh** | All 7 production CSV extracts present in `powerbi/data/` | File system inspection & row count check | **PASS** | `Sales` (34,007 rows), `Inventory` (449 rows), `Product` (60 rows), `Customer` (800 rows), `Location` (8 rows), `Date` (2,192 source rows; 730 rows retained in the report after Power Query filtering), `DataQualityReconciliation` (8 rows) verified. |
| **Data Extracts & Refresh** | Local CSV data refresh inside Power BI Desktop | Analysis Services cache verification | **PASS** | `cache.abf` populated; Power BI Desktop successfully loads and synchronizes all tables. |
| **Parameter Architecture** | Portability of `DataFolder` Power Query parameter | Model inspection & test assertion | **PASS** | Configured under `expressions.tmdl` / `model.bim`; handles paths with/without trailing slash; editable via Desktop UI or `build_powerbi_pbip.py`. |
| **Model Relationships** | 6 active single-direction star-schema relationships | TMDL & relationship integrity script | **PASS** | 0 orphan foreign keys; dimension primary keys are 100% unique; data types match. |
| **DAX Measures** | Mathematical correctness of 45+ DAX measures | Independent Python calculation vs TMDL formulas | **PASS** | Net Revenue (₹209.03M), Gross Profit (₹42.36M), Margin (20.26%), Orders (7,878), AOV (₹26,534), Items Needing Action (92) verified. |
| **Report Pages** | 4 intended analytical report pages defined in order | `pages.json` and `page.json` validation | **PASS** | 1. Executive Profitability, 2. Margin Investigation, 3. Inventory Decisions, 4. Data Integrity & Pipeline Assurance. |
| **Visual Bindings** | PBIR & `report.json` visual queryState & prototypeQuery bindings | Automated audit (`audit_visual_bindings.py`) | **PASS** | All 28 visuals across all 4 pages have valid `queryState` and `prototypeQuery` referencing existing model measures and columns. 0 unresolved references. |
| **Visual Headers** | Textbox header paragraph & textRun formatting | PBIR & report.json schema inspection | **PASS** | All 4 page headers populated with titles in Segoe UI Semibold. |
| **Date Type Conversion** | Missing date handling (`vw_dim_customer.csv` & `vw_fact_inventory.csv`) | Power Query M null replacement & ISO date typing | **PASS** | VertiPaq conversion error resolved. Empty strings `""` mapped to `null` via `Table.ReplaceValue`; `signup_date`, `first_order_date`, `last_order_date`, `snapshot_date`, `last_restocked_date` typed to `date`. |
| **Date Dimension Keys** | Date dimension key typing (`dim_date.csv` `date_key`) & `Sales_Date` relationship | Power Query M date typing & VertiPaq relationship integrity | **PASS** | Resolved `Revenue by year_month` single `(Blank)` point issue. `Date.date_key` typed to `date` / `dateTime` in M and TMDL, matching `Sales.order_date` (100% key match, 34,007 rows). |
| **Data Assurance Types** | `DataQualityReconciliation` numeric typing (`int64`, `double`) & M transformation | Live SSAS query & unit test assertions | **PASS** | Resolved Page 4 card visual errors. Columns `raw_ingested`, `exact_duplicates_dropped`, `quarantined_rejected`, `merged_deduplicated`, `clean_loaded` typed to `int64` and `preservation_rate` to `double` in TMDL and M partition. |
| **Automated Tests** | Power BI deliverable unit test suite | `pytest tests/test_powerbi_deliverable.py` | **PASS** | 12 passed in 0.24s, 0 failures (includes data assurance type validation). |
| **Full Regression Suite**| Full repository test suite | `pytest tests/ -v` | **PASS** | Original offline snapshot: 160 passed and 69 skipped because PostgreSQL was unavailable. The database-enabled GitHub Actions run on 24 October 2026 passed 233 tests with zero failures; blocking Ruff lint and formatting checks passed. |
| **Interactive Slicers** | Cross-filtering & visual interactions | Model schema & PBIR layout | **PASS** | Dimensional relationships filter facts as intended; date slicer reaches Sales and is isolated from Inventory snapshot. |
| **VertiPaq Cache Persistence** | Retention of local database `.pbi/cache.abf` across project rebuilds | Build script verification & FS inspection | **PASS** | `build_powerbi_pbip.py` preserves local VertiPaq cache by default, preventing repeated uncalculated table/relationship warnings. |
| **Relationship Parity** | Parity of 6 model relationships before and after save/refresh | TMDL & model comparison | **PASS** | 0 relationships altered; yellow warning was an artifact of uncalculated relationships in an empty VertiPaq DB. |
| **Auto-Recovery Isolation** | Disambiguation of `InsightFlow_UpgradeExploration *.pbix` vs main PBIP | Process and path tracing | **PASS** | Auto-recoveries traced to Power BI Desktop Store App `TempSaves\Backups`; main PBIP remains authoritative. |
| **Desktop Rendering** | Visual canvas rendering in Power BI Desktop GUI | Live Desktop Bridge inspection | **PASS** | Verified across all 4 pages in running Power BI Desktop GUI; cards, charts, and tables render with real data and 0 errors. |
| **Runtime Screenshots** | Live Desktop screenshots of all 4 pages | Power BI Desktop Bridge CLI capture | **PASS** | Genuine runtime screenshots of all 4 pages captured into `screenshots/powerbi/` and visually audited with 0 blank cards or banners. |

---

## 2. Unfiltered KPI Checkpoint Benchmarks

All benchmark values verified independently against the raw transaction records in `powerbi/data/vw_fact_sales.csv` and `vw_fact_inventory.csv`:

- **Net Revenue:** ₹209,034,798.31 (₹209.03M)
- **Gross Profit:** ₹42,355,329.09 (₹42.36M)
- **Gross Margin %:** 20.26%
- **Completed Orders:** 7,878
- **Average Order Value (AOV):** ₹26,534.00
- **Active Customers:** 780
- **Items Needing Action:** 92 positions (Out of stock: 39, Risk: 39, Low: 14)
- **Flagship Case Study (Basmati Rice 5kg / P0010):**
  - Net Revenue: ₹16,534,420.00
  - Gross Profit: ₹355,958.00
  - Margin %: 2.15%
  - Break-Even Volume Tolerance (+3% price): 58.3%
- **Inventory Capital Replenishment:**
  - Replenishment Qty Required: 5,791 units
  - Working Capital Estimate: ₹966,456.00 (₹9.66 L)
  - Catalog Stock Gap Retail Valuation: ₹1,341,250.00 (₹13.41 L)
- **Pipeline Data Assurance:**
  - Raw Records Ingested: 49,975
  - Clean Records Loaded: 47,814
  - Exact Duplicates Dropped: 512
  - Quarantined / Rejected Records: 1,609
  - Merged Profiles: 40
  - Overall Data Preservation Rate: 95.7% (Reconciliation Law: $49,975 - 512 - 1,609 - 40 = 47,814$)

---

## 3. Customer & Inventory Date Conversion Repair Details

### Diagnostic Summary
When opening the PBIP project in Power BI Desktop (v2.159.883.0 / October 2026), VertiPaq failed during semantic model load:
```text
Datatype conversion failed for [Table: '', Column: '', Value: '']. (Customer (19); first order date (86))
Datatype conversion failed for [Table: '', Column: '', Value: '']. (Customer (19); signup date (85))
```

### Root Cause
1. **Empty Fields in CSV Extracts**:
   - `vw_dim_customer.csv` (800 rows):
     - `signup_date`: 17 rows with empty strings `""` (unrecorded registration dates).
     - `first_order_date` & `last_order_date`: 20 rows with empty strings `""` (customers in "No purchases" segment who have never ordered).
     - 0 invalid or malformed dates (all populated dates strictly follow ISO `YYYY-MM-DD`).
   - `vw_fact_inventory.csv` (449 rows):
     - `last_restocked_date`: 5 rows with empty strings `""`.
     - `days_of_cover`: 20 rows with empty strings `""` (zero run-rate items).
2. **Untransformed Power Query M Queries**:
   - In both `CustomerPartition` and `InventoryPartition`, `Csv.Document` loaded empty fields as text `""`.
   - The Tabular model defined these columns as `dataType: dateTime`.
   - When VertiPaq imported text `""` into a `dateTime` column, the type conversion failed and aborted the model transaction.
3. **Stale VertiPaq Analysis Services Cache (`cache.abf`)**:
   - When Power BI Desktop opens a `.pbip` project, `LocalAnalysisServicesDatabaseCreator` first checks for `.pbi/cache.abf` and calls `LoadDatabaseFromStreamAndSchema`.
   - The pre-existing `cache.abf` (saved prior to type migration) contained the 800 cached Customer rows with `""` as string.
   - Immediately upon restoring the stream, `TmslApplier.ApplyTmsl` called `TomDatabase.Update` to apply `model.bim` schema changes (converting `Customer.signup_date` and `first_order_date` to `dateTime`).
   - VertiPaq attempted in-place conversion of the cached `""` values in memory and threw:
     `Datatype conversion failed for [Table: '', Column: '', Value: '']. (Customer (19); first order date (86))`
   - Deleting stale `.pbi/cache.abf` and `.pbi/localSettings.json` forces Power BI Desktop to call `CreateEmptyDatabase`, creating a clean tabular database from `model.bim` and populating it via Power Query M without in-place migration conflicts.

### Resolution
1. **Power Query M Normalization**:
   - Added `Table.ReplaceValue(#"Promoted Headers", "", null, Replacer.ReplaceValue, {"signup_date", "first_order_date", "last_order_date"})` to convert empty strings to real `null` values.
   - Added `Table.TransformColumnTypes` parsing valid ISO strings to `type date` using invariant `"en-US"` formatting.
   - Applied identical handling to `InventoryPartition` for `last_restocked_date` and `days_of_cover`.
2. **Semantic Model Metadata Alignment**:
   - Updated both `model.bim` and TMDL (`Customer.tmdl`, `Inventory.tmdl`) with `dataType: dateTime` and `formatString: yyyy-mm-dd`.
   - Updated PBIP generator script `scripts/build_powerbi_pbip.py` to ensure future regenerations preserve the exact Power Query transformations and column metadata.
3. **Stale VertiPaq Analysis Services Cache Eviction**:
   - Removed stale `.pbi/cache.abf` and `.pbi/localSettings.json` from `powerbi/InsightFlow.SemanticModel/.pbi/`.
   - Updated `scripts/build_powerbi_pbip.py` to automatically purge stale `.pbi/cache.abf` upon rebuild, guaranteeing that Power BI Desktop initializes a fresh tabular model directly from `model.bim` using `CreateEmptyDatabase`.
4. **Automated Verification**:
   - Added `test_customer_date_columns_and_powerquery_handling` and `test_inventory_date_columns_and_powerquery_handling` to `tests/test_powerbi_deliverable.py`.
   - Verified 800 rows preserved, 17/20 exact null distributions, ISO format validation, and M query AST structure.

---

## 4. Blank Visuals Root-Cause & PBIR 4.0 Visual Resolution Details

### Diagnostic Summary
When opening the PBIP project in Power BI Desktop (v2.159.883.0 / October 2026), all tables refreshed successfully and synchronized, but report visuals across the canvas displayed empty wireframe placeholders reading:
`(i) Select or drag fields to populate this visual`

### Root Cause
1. **Dual Report Definition Conflict & Serialization Stripping**:
   - `scripts/build_powerbi_pbip.py` previously generated a legacy `InsightFlow.Report/report.json` with `"singleVisual": {"projections": ...}` while `definition.pbir` was set to `"version": "1.0"`.
   - Power BI Desktop PBIP architecture treats `"version": "1.0"` as legacy format and expects legacy `prototypeQuery` structures inside `report.json`.
   - Because `report.json` lacked legacy `prototypeQuery` constructs, Desktop treated the visuals as unpopulated placeholders.
   - Upon Desktop save (or synchronization), Power BI Desktop auto-migrated `report.json` into modern PBIR format (`definition/pages/*/visuals/*/visual.json`), stripping empty visual states and deleting `report.json`.
2. **Modern PBIR Card Visual Schema Incompatibility**:
   - Modern PBIR (`visualContainer/2.13.0` / Microsoft Fabric schema) deprecates `"visualType": "card"` with query role `"Values"`.
   - Modern PBIR requires `"visualType": "cardVisual"` with projection role **`"Data"`**!
   - When Desktop parsed `"visualType": "card"`, it unrecognized the query role and discarded visual field bindings.
3. **Bar Chart Visual Type Identifier**:
   - Modern PBIR uses `"visualType": "clusteredBarChart"` rather than `"barChart"`.

### Resolution
1. **PBIR Visual Generator Update (`scripts/generate_pbir_visuals.py`)**:
   - Updated JSON schema URL to Fabric standard: `https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json`.
   - Standardized all KPI card visuals to `"visualType": "cardVisual"` with role `queryState.Data.projections`.
   - Standardized bar charts to `"visualType": "clusteredBarChart"`.
   - Formatted textboxes with compliant `objects.general[0].properties.paragraphs[0].textRuns` styling.
2. **PBIP Project Entry Point Alignment (`scripts/build_powerbi_pbip.py`)**:
   - Configured `definition.pbir` to use Microsoft Fabric's official definition properties schema:
     `$schema: "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/1.0.0/schema.json"` with `"version": "1.0"`.
   - Configured `definition.pbism` to use Microsoft Fabric's official semantic model schema:
     `$schema: "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json"` with `"version": "1.0"`.
   - Generated complete root `InsightFlow.Report/report.json` via `scripts/generate_report_json.py` with full `prototypeQuery` and `projections` across all 28 visuals on all 4 pages. This ensures Power BI Desktop immediately renders the report out-of-the-box even without requiring preview feature flags.
   - Preserved all 28 modern PBIR `visual.json` files in `definition/pages/*/visuals/` for environments where the enhanced report format preview is enabled.
3. **Automated Verification**:
   - All 11 Power BI deliverable tests in `tests/test_powerbi_deliverable.py` pass.
   - The original offline run skipped database-dependent tests; the database-enabled GitHub Actions revalidation on 24 October 2026 passed 233 tests with zero failures.

---

## 5. Date Dimension Type Alignment & `Sales_Date` Relationship Repair

### Diagnostic Summary
When opening the Executive Profitability Overview page in Power BI Desktop, KPI cards rendered correct totals and category revenue displayed as expected, but the visual titled `Revenue by year_month` (Monthly Net Revenue Trend) rendered as a single point with `(Blank)` on the x-axis instead of 24 monthly revenue data points.

### Root Cause
1. **Power Query M Missing Type Transformation for Date Table**:
   - `DatePartition` loaded `dim_date.csv` with `Csv.Document` and `Table.PromoteHeaders` without a `Table.TransformColumnTypes` step.
   - Power Query inferred all columns in `Date` as text (`type text`), leaving `date_key` as a text string (e.g., `"2024-10-01"`).
2. **Semantic Model Data Type Mismatch**:
   - In `definition/tables/Date.tmdl`, `column date_key` had `dataType: string`.
   - In `definition/tables/Sales.tmdl`, `column order_date` had `dataType: dateTime`.
3. **VertiPaq Relationship Failure**:
   - In Analysis Services / VertiPaq, the active star-schema relationship `Sales_Date` (`Sales.order_date -> Date.date_key`) joined a `dateTime` column to a `string` column.
   - Because the data types mismatched, VertiPaq failed to resolve keys across the relationship.
   - When grouping `Sales.Revenue` by `Date.year_month`, all 34,007 sales transactions failed to find matching rows in `Date` and aggregated into the `(Blank)` date category for a single total of ₹209,034,798.31.

### Resolution
1. **Power Query M Normalization**:
   - Added explicit `Table.TransformColumnTypes` to `DatePartition`:
     `{"date_key", type date}, {"year", Int64.Type}, {"quarter", Int64.Type}, {"quarter_name", type text}, {"month", Int64.Type}, {"month_name", type text}, {"year_month", type text}, {"day", Int64.Type}, {"day_of_week", Int64.Type}, {"day_name", type text}, {"is_weekend", type logical}` using invariant `"en-US"`.
2. **Semantic Model Alignment**:
   - Aligned `Date.tmdl` to declare `column date_key` as `dataType: dateTime` with `formatString: yyyy-mm-dd`, `UnderlyingDateTimeDataType = Date`, and integer/boolean typing for other dimension attributes.
   - Synchronized `model.bim` and updated `scripts/build_powerbi_pbip.py` to persist the M transformation and TMDL alignment on every rebuild.
   - Evicted stale `.pbi/cache.abf` to ensure VertiPaq rebuilds tabular storage with native date matching.
3. **Visual Chronological Ordering**:
   - Added ascending chronological `OrderBy` on `Date.year_month` in `scripts/generate_report_json.py` so the 24 monthly data points render sequentially from `2024-10` to `2026-09`.
4. **Three Other Pages Audit**:
   - Page 2 (`Margin Investigation`): Verified all 7 visuals. All joins route through `Sales_Product` (`product_id` string-to-string), 0 type mismatches.
   - Page 3 (`Inventory Decisions`): Verified all 8 visuals. Uses `Inventory` measures and string-to-string joins (`product_id`, `location_id`).
   - Page 4 (`Data Integrity & Pipeline Assurance`): Verified all 5 visuals. Directly queries `DataQualityReconciliation` fact table.
   - Total visual audit across all 4 pages: 28 visuals audited, 0 unresolved references, 100% field alignment.

---

## 6. Analysis Services Cache Lifecycle, Auto-Recovery Disambiguation & Acceptance Protocol

### Diagnostic Summary
When opening the generated PBIP project in Power BI Desktop, users reported:
1. Yellow warning banners on launch:
   - *"One or more relationships have been modified and need to be refreshed manually."*
   - *"Some of the tables have incomplete or no data."*
2. Clicking **Refresh** successfully loads all tables and populates the canvas.
3. Upon closing and reopening the project, the refresh warnings reappear.
4. Auto-recovery snapshots titled `InsightFlow_UpgradeExploration 5` appeared in Power BI Desktop.

### Confirmed Facts vs Assumptions

#### Confirmed Facts:
1. **Primary Project Filesystem Paths**:
   - Project Root PBIP: `powerbi/InsightFlow.pbip`
   - Report Folder: `powerbi/InsightFlow.Report/` (`definition.pbir`, `report.json`, `definition/pages/`)
   - Semantic Model Folder: `powerbi/InsightFlow.SemanticModel/` (`definition.pbism`, `model.bim`, `definition/tables/`, `.pbi/`)
   - Source CSV Data: `powerbi/data/` (7 CSV files, 34,007 sales rows)
2. **Auto-Recovery File Source (`TempSaves\Backups`)**:
   - The files `InsightFlow_UpgradeExploration *.pbix` are located in:
     `%USERPROFILE%\Microsoft\Power BI Desktop Store App\TempSaves\Backups\`
   - These are created strictly by the Windows Store edition of Power BI Desktop (`PBIDesktopStore`) as an auto-recovery safety mechanism whenever a session closes without saving or terminates unexpectedly.
   - When Desktop opens after an abnormal exit, it prompts the user to recover session files. Selecting a recovered session loads an isolated `.pbix` clone in `TempSaves` rather than opening the version-controlled `powerbi\InsightFlow.pbip`.
3. **VertiPaq Cache Behavior (`.pbi/cache.abf`)**:
   - Power BI Desktop stores cached VertiPaq columnar data inside `powerbi/InsightFlow.SemanticModel/.pbi/cache.abf`.
   - In `scripts/build_powerbi_pbip.py` (lines 28–33), `build_pbip()` was unconditionally calling `cache_abf.unlink()` and `local_settings.unlink()`.
   - Whenever `build_powerbi_pbip.py` ran to generate or update PBIP schemas, it deleted `cache.abf`.
   - When Desktop opens a PBIP project without `cache.abf`, Analysis Services initializes an empty tabular database (0 rows in memory). Because the tables contain no data and the 6 relationships are uncalculated, Desktop generates the standard warnings:
     - *"Some of the tables have incomplete or no data."*
     - *"One or more relationships have been modified and need to be refreshed manually."*
4. **Relationship Parity (No Modifications)**:
   - A comparison of `model.bim`, `relationships.tmdl`, and historical backups confirms that all 6 star-schema relationships remained completely unchanged.
   - The warning *"One or more relationships have been modified"* is the standard Analysis Services notification for uncalculated relationships in an unpopulated tabular database, not an indication that definitions were altered.

#### Tested Assumptions:
- *Assumption:* Power BI Desktop was discarding relationship metadata upon save.
  - *Finding:* Refuted. `relationships.tmdl` and `model.bim` retain identical definitions before and after save.
- *Assumption:* A background script was periodically creating backups in the repository.
  - *Finding:* Refuted. No script in the repository creates `.pbix` backups; the files are native Power BI Desktop Store App auto-recoveries.

### Resolution
1. **Cache Retention in PBIP Builder**:
   - Updated `scripts/build_powerbi_pbip.py` so that `build_pbip(clean_cache: bool = False)` retains `.pbi/cache.abf` and `.pbi/localSettings.json` by default.
   - Cache purge is now strictly opt-in via the `--clean-cache` CLI flag (used only during breaking schema migrations).
   - Once the user refreshes and saves in Power BI Desktop, `cache.abf` persists, enabling subsequent launches without data refresh prompts or warnings.
2. **Git Hygiene**:
   - Confirmed `.gitignore` excludes `powerbi/**/*.abf` and `.pbi/localSettings.json`, preventing binary data caches from polluting version control.

### Acceptance Test Protocol
To verify the end-to-end resolution:
1. **Launch**: Launch `powerbi/InsightFlow.pbip` directly in Power BI Desktop. (If prompted with "Auto-recovery: We recovered...", click **Discard all** to avoid opening orphaned `TempSaves` `.pbix` files).
2. **First Refresh**: Click **Home > Refresh**. All 7 tables load cleanly from `powerbi/data/`.
3. **Save**: Click **File > Save** (or `Ctrl+S`). Power BI Desktop writes VertiPaq tabular storage to `powerbi/InsightFlow.SemanticModel/.pbi/cache.abf`.
4. **Close Cleanly**: Close Power BI Desktop via `Alt+F4` or the window close button.
5. **Reopen**: Open `powerbi/InsightFlow.pbip`. Power BI Desktop loads from `cache.abf` with **0 warnings**, tables fully populated, and all visuals displaying live metrics immediately.
6. **Rebuild Resilience**: Running `python scripts/build_powerbi_pbip.py` regenerates report and model JSON definitions without evicting `cache.abf`. Reopening Desktop continues to open instantly with 0 warnings.

---

## 7. Page 4 Data Assurance Visual Failure Root Cause & Type-Safety Resolution

### Diagnostic Summary
In the live Power BI Desktop session:
1. Pages 1, 2, and 3 rendered live metrics and charts cleanly after refresh.
2. On Page 4 (`Data Integrity & Pipeline Assurance`), the 3 KPI cards (`CardTotalRaw`, `CardTotalClean`, `CardPreservationRate`) displayed:
   `Error fetching data for this visual See details`.
3. Meanwhile, the table visual `ReconciliationMatrixTable` rendered all 8 entity rows cleanly.

### Live Engine Empirical Investigation
Using a direct ADOMD connection to the running Analysis Services instance (`msmdsrv.exe`, PID 13408, port 60441):
1. **Table Population Verification:**
   - `Sales`: 34,007 rows
   - `Inventory`: 449 rows
   - `Product`: 60 rows
   - `Customer`: 800 rows
   - `Location`: 8 rows
   - `Date`: 1,004 rows
   - `DataQualityReconciliation`: 8 rows
   All 7 tables are genuinely populated in VertiPaq columnar storage.
2. **Field & Relationship Verification:**
   - `Location[region]` alone returned all 4 regions: `West`, `North`, `South`, `East`.
   - `SUMMARIZECOLUMNS(Location[region], [Revenue])` returned expected figures: West (₹74.86M), North (₹46.18M), South (₹74.34M), East (₹13.66M). Location relationships and measure evaluations function properly.
3. **DAX Error Isolation:**
   - Direct DAX query `EVALUATE ROW("Val", SUM(DataQualityReconciliation[raw_ingested]))` threw:
     `"The function SUM cannot work with values of type String."`
   - Direct DAX query `EVALUATE ROW("Val", [Total Raw Records])` threw:
     `"Calculation error in measure 'DataQualityReconciliation'[Total Raw Records]: The function SUM cannot work with values of type String."`

### Root Cause
- In `powerbi/InsightFlow.SemanticModel/definition/tables/DataQualityReconciliation.tmdl`, columns `raw_ingested`, `exact_duplicates_dropped`, `quarantined_rejected`, `merged_deduplicated`, `clean_loaded`, and `preservation_rate` were declared as `dataType: string`.
- In `ReconciliationPartition`, the Power Query M expression lacked a `Table.TransformColumnTypes` step, causing CSV string headers to load raw records as text strings.
- Because DAX `SUM` requires numeric columns, the three KPI card visuals failed with a calculation error.
- In contrast, `ReconciliationMatrixTable` rendered without error because tabular columns without summarization can display strings directly.

### Corrective Action Applied
1. Updated `DataQualityReconciliation.tmdl`:
   - Numeric columns typed to `dataType: int64` with `formatString: #,0` and `summarizeBy: sum`.
   - `preservation_rate` typed to `dataType: double` with `formatString: 0.0%`.
   - Power Query M partition updated with:
     `Table.TransformColumnTypes(#"Promoted Headers", {{"table_name", type text}, {"raw_ingested", Int64.Type}, {"exact_duplicates_dropped", Int64.Type}, {"quarantined_rejected", Int64.Type}, {"merged_deduplicated", Int64.Type}, {"clean_loaded", Int64.Type}, {"reconciliation_status", type text}, {"preservation_rate", type number}}, "en-US")`
2. Updated `scripts/build_powerbi_pbip.py` to synchronize both `model.bim` and `DataQualityReconciliation.tmdl` with typed definitions on regeneration.
3. Added automated unit regression test `test_data_assurance_reconciliation_model_and_powerquery_handling` in `tests/test_powerbi_deliverable.py` (12/12 passing).

---

## 8. Release Gate Verdict

### Recommendation: **FULL GO**

#### Rationale:
1. **All Programmatic & Visual Gates Pass (PASS):**
   - The root cause of the `Revenue by year_month` single `(Blank)` point has been diagnosed and resolved: `Date.date_key` typed to `dateTime` matching `Sales.order_date` with 100% key coverage (34,007 / 34,007 rows).
   - The root cause of the Page 4 `Data Integrity` card visual failure has been diagnosed and resolved: numeric columns typed to `int64` and `double` in TMDL and M partition, resolving the DAX `SUM` error.
   - Dual report definition architecture (`report.json` with VertiPaq `prototypeQuery` + modern PBIR `definition/`) ensures out-of-the-box rendering in Power BI Desktop.
   - All 6 star-schema relationships are active with matching types and 0 orphan keys.
   - VertiPaq cache persistence issue resolved; `cache.abf` is retained across PBIP rebuilds, preventing repeated refresh warnings on launch.
   - Historical offline test counts are superseded by the database-enabled GitHub Actions run on 24 October 2026: 233 tests passed, zero failures, and Ruff lint/format checks passed.
2. **Desktop Visual Verification Complete:**
   - User confirmed live visual rendering in Power BI Desktop.
   - All four report pages successfully captured via Power BI Desktop Bridge CLI into `screenshots/powerbi/` and visually inspected with 0 errors, 0 blank cards, and populated data across all tables and charts.
