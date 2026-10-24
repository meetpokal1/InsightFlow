# Engineering Rationale & System Concepts

This document details the architectural principles, data governance rules, and analytical methodologies implemented across InsightFlow. It explains why specific engineering decisions were made across the data pipeline, PostgreSQL database, FastAPI service, and Power BI semantic model.

---

## 1. Pipeline Architecture & Ingestion Principles

### Text-First Ingestion (`dtype=str`)
When ingesting raw CSV and Excel files, all columns are initially loaded as text (`dtype=str` in pandas / text format in Power Query). Allowing automated type inference introduces critical failure modes:
- **Identifier Distortion:** Alphanumeric codes or numeric IDs with leading zeros (e.g., product code `007`) are coerced into integers, permanently losing significant digits.
- **Float Conversion via Missing Values:** In older NumPy/pandas semantics, an integer column containing a single missing value is coerced to IEEE-754 `float64` (e.g., quantity `12` becoming `12.0`).
- **Date Ambiguity:** Ambiguous dates (e.g., `05/03/2025`) may be arbitrarily coerced to US format (May 3rd) rather than intended UK/Indian format (March 5th).
- **String Currency Markers:** Columns containing symbols such as `₹` or commas cannot be converted to numeric without explicit cleaning.

Reading raw inputs as raw text ensures that all sanitization, format detection, and type casts are explicit, reproducible, and testable in code.

### Deterministic Repair vs. Quarantine Logging
The pipeline enforces a strict boundary between repairable anomalies and unresolvable defects:
- **Deterministic Repair:** Applied only when the ground truth can be derived unambiguously (e.g., trimming whitespace, normalizing casing, parsing standardized date strings, stripping currency formatting, or looking up catalog list prices for missing prices).
- **Quarantine Isolation:** Applied when data is missing or corrupted without a safe fallback (e.g., orphaned foreign keys, invalid transaction dates, negative quantities, or corrupted customer IDs). Defective rows are isolated into diagnostic quarantine files (`data/processed/*_quarantine.csv`) with explicit error reasons—they are never silently discarded.

### Validation Gates & Atomic Relational Loading
Data cleansing executes in topological order across entity dependencies:
1. `categories` &rarr; 2. `suppliers` &rarr; 3. `locations` &rarr; 4. `products` &rarr; 5. `customers` &rarr; 6. `orders` &rarr; 7. `order_items` &rarr; 8. `inventory`.

Before any database write occurs, pre-load validation gates inspect foreign key integrity, uniqueness constraints, and allowable value ranges (`src/cleaning/validators.py`). If a single validation check fails, the execution terminates before touching the database.

Database loading executes within a single database transaction (`engine.begin()`): all tables are truncated and repopulated atomically. If an insert fails, PostgreSQL automatically rolls back the entire transaction, leaving the prior operational database intact.

---

## 2. Cleansing Decisions & Entity Resolution

### Exact Deduplication vs. Business Deduplication
- **Exact Duplicates:** Identical rows across all columns, typically caused by ingestion re-runs or duplicate export batches. These are safely dropped.
- **Business Duplicates:** The same real-world entity registered under multiple customer IDs (e.g., matching email addresses, or matching normalized names and phone numbers). The pipeline retains the earliest active record as canonical, merges profile details, and executes an ID remapping step across historical child orders (`remap_ids` in `src/cleaning/customers.py`).

### Derived Metrics at Source
The pipeline discards raw summary columns such as `orders.order_total`. Raw total headers in legacy source extracts frequently diverge from the sum of line items due to unrecorded discounts, partial returns, or rounding discrepancies. To maintain absolute transactional consistency, order totals, net revenues, and gross margins are calculated strictly from individual verified `order_items` records.

---

## 3. Database Architecture & Relational Design

### Canonical PostgreSQL Views as Single Source of Truth
To prevent metric drift between operational reports, APIs, and business intelligence models, core business calculations are centralized directly in PostgreSQL views (`sql/schema/04_views.sql`):
- `vw_fact_sales`: Line-item net revenue, cost of goods sold, and gross margins.
- `vw_fact_inventory`: Point-in-time stock valuation, run-rate cover days, and inventory health classification.
- `vw_customer_segments`: Recency, frequency, monetary (RFM) scoring and segment assignment.

The SQL analytics suite, FastAPI REST endpoints, and Power BI semantic model query these identical definitions, ensuring 100% calculation parity across all access channels.

### Exact Decimal Precision (`NUMERIC(12,2)`)
Financial values (unit prices, net revenues, inventory valuations, taxes) are strictly typed as `NUMERIC(12,2)` in PostgreSQL and `Currency` / `Decimal` in Power BI. Binary floating-point types (`FLOAT`, `REAL`, `float64`) introduce IEEE-754 rounding artifacts that accumulate over millions of records, corrupting financial balances and balance sheet reconciliations.

### Star Schema Dimensional Modeling
The analytical layer implements a single-direction star schema centered on two fact tables:
- `Sales` (transactional order lines)
- `Inventory` (operational stock snapshot)

These facts are filtered by four conformant dimension tables: `Date`, `Product`, `Customer`, and `Location`. All relationships are configured as 1:N single-direction relationships from dimension to fact. Many-to-many and bi-directional cross-filtering are intentionally avoided to ensure deterministic filter propagation, prevent circular query paths, and optimize columnar compression.

---

## 4. Analytical Methodology & Business Logic

### Gross Margin vs. Markup
- **Gross Margin:** Profit expressed as a percentage of revenue: $\frac{\text{Gross Profit}}{\text{Revenue}}$.
- **Markup:** Profit expressed as a percentage of cost: $\frac{\text{Gross Profit}}{\text{Cost of Goods}}$.

InsightFlow standardizes on Gross Margin across all executive KPI cards, SQL queries, and Power BI visuals.

### Flagship Elasticity & Break-Even Volume Decline
For thin-margin volume drivers (such as Basmati Rice 5kg / `P0010`, generating ₹16.53M net revenue at a 2.15% gross margin), standard price increases cannot be modeled purely through static multipliers. A price increase of +3% expands unit gross margin significantly.

The break-even volume decline metric models the maximum tolerable drop in sales volume before total gross profit falls below the pre-price-increase baseline:
$$\text{Break-Even Volume Decline \%} = 1 - \frac{\text{Baseline Gross Profit}}{(\text{New Price} \times \text{Baseline Units}) - (\text{Unit Cost} \times \text{Baseline Units})}$$
For Basmati Rice 5kg, a +3% price hike allows up to a **58.3% decline in sales volume** before commercial gross profit is impaired, uncovering pricing power in essential commodity lines.

### Inventory Health Classification & Run-Rate Cover
Inventory positions are classified dynamically based on daily sales velocity over a 90-day window:
- **Out of stock:** 0 units on hand.
- **Stock-out risk:** Days of cover is less than supplier lead time (stock will deplete before an order placed today can arrive).
- **Low stock:** Units on hand are below the defined reorder level, but cover exceeds immediate lead time.
- **Overstocked:** Days of cover exceeds 180 days, tying up working capital.
- **Healthy:** Stock cover is sufficient to meet lead time and safety thresholds without excessive working capital tie-up.

---

## 5. Testing Strategy & Assurance Invariants

### Pipeline Balancing & Conservation Law
Every ETL execution is audited against the universal conservation equation:
$$\text{Raw Ingested} - \text{Exact Duplicates} - \text{Quarantined} - \text{Merged} = \text{Clean Loaded}$$
This reconciliation equation is tracked per entity in `etl_quality_log` and summarized in `data_assurance_reconciliation.csv`. Page 4 of the Power BI report and `tests/test_workpaper.py` assert that 100% of ingested records are accounted for without silent drops.

### Dual-Engine Calculation Parity
The test suite enforces dual-engine parity: SQL view outputs and FastAPI responses are programmatically verified against independent pandas calculations running on the same raw dataset. If an underlying formula or grouping rule changes inconsistently in either engine, CI assertions immediately fail.

### Synthetic Data Ground Truth Validation
Synthetic test data is injected with predetermined error profiles recorded in `_generation_manifest.json`. Regression tests verify that the cleansing pipeline recovers at least 90% of injected anomalies while generating zero false-positive rejections.
