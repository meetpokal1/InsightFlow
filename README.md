# InsightFlow — Retail Decision-Intelligence & Data-Quality Engineering Case Study

[![Tests](https://github.com/meetpokal1/InsightFlow/actions/workflows/tests.yml/badge.svg)](https://github.com/meetpokal1/InsightFlow/actions/workflows/tests.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-336791.svg)](https://www.postgresql.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.42+-FF4B4B.svg)](https://streamlit.io/)
[![Power BI](https://img.shields.io/badge/Power%20BI-PBIP%20%7C%20TMDL-F2C811.svg)](https://powerbi.microsoft.com/)
[![Code style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> **Live Hosted Demo:** [insightflow-portfolio.streamlit.app](https://insightflow-portfolio.streamlit.app/)  
> **Interactive Local Execution (No Database Required):** `streamlit run streamlit_app.py`  
> **Data Defect & Decision Impact Audit CLI:** `python scripts/run_defect_impact.py`  
> **Dataset Provenance Notice:** All business figures, transactions, and entity names are seeded from an audited, deterministic synthetic retail benchmark (49,975 raw records).

---

## 1. Project Thesis: Bridging Data Hygiene and Commercial Decisions

A business cannot make dependable profitability or inventory decisions from unvalidated exports. In retail and wholesale distribution, raw extracts from Point of Sale (POS) terminals, e-commerce storefronts, accounting packages, and warehouse systems arrive with inconsistent formatting, duplicate entities, extreme quantity typos, and conflicting header totals. 

When analytics teams load raw exports directly into reporting tools, these defects propagate silently into executive dashboards:
- In our audited synthetic benchmark, naive line-item aggregation inflates gross revenue by **+105.7% (+₹220.90M)** due to unquarantined quantity outliers and decimal displacement.
- Inconsistent invoice headers introduce an unaccounted **₹5.72M** variance across 1,312 orders.
- Unresolved customer identities fracture **₹5.87M** across 50 duplicate ghost profiles, distorting wholesale purchasing tiers and repeat loyalty rates.
- Unhandled column swaps flip product costs and selling prices, generating a false **-₹2.87M loss** on profitable audio hardware and risking wrongful SKU delisting.
- Missing reorder levels blind inventory managers to replenishment needs across **18 product locations**.

**InsightFlow** demonstrates how to engineer an auditable, end-to-end decision-intelligence pipeline. It establishes strict data hygiene gates, deterministic entity reconciliation, star-schema relational modeling, a FastAPI service layer, an interactive Streamlit decision simulator, an Excel audit workpaper, and a version-controlled Power BI project (`InsightFlow.pbip`). Every transformation is backed by automated tests, mathematical checksums, and transparent audit logging.

```
┌─────────────────┐     ┌───────────────────────┐     ┌────────────────────────┐     ┌────────────────────────┐
│  Raw Multi-     │     │  Python Validation &  │     │  PostgreSQL Relational │     │  Operational Decision  │
│  Format Exports │ ──> │  Quality Pipeline     │ ──> │  Star Schema & Views   │ ──> │  Surfaces (API, UI,    │
│  (CSV & XLSX)   │     │  (Sanitize & Check)   │     │  (Audited Baseline)    │     │  Power BI & Excel)     │
└─────────────────┘     └───────────────────────┘     └────────────────────────┘     └────────────────────────┘
         │                          │                             │                              │
   49,975 records             512 duplicates               ₹209.03M Net Rev               Break-even simulators,
   15,052 injected            1,609 quarantined            20.3% Gross Margin             replenishment queues,
   source defects             40 customer merges           449 inventory SKUs             traceability matrices
```

---

## 2. The Business Problem

Consider a mid-market multi-location distributor operating 8 regional hubs, 60 product SKUs, and 800 commercial accounts. Transactional data arrives weekly as separate CSV and Excel extracts from disconnected legacy systems. 

Without an automated data-quality pipeline, common data failure modes undermine decision-making:
1. **Quantity Outliers & Keying Errors:** Warehouse staff occasionally key order quantities as `5000` or `25000` instead of standard pack sizes, or enter negative quantities (`-5`) to record return adjustments. In naive aggregations, these outliers distort demand velocity and inflate turnover by 2.2x.
2. **Decimal Displacements:** Supplier price catalog updates occasionally shift decimals (`100.0x` or `0.01x`) or swap cost and selling prices. An automated report that fails to catch inverted pricing flags top-performing SKUs (such as Bluetooth Earbuds) as loss-makers, prompting wrongful vendor renegotiations or SKU cancellation.
3. **Split Customer Identities:** Customers register again under slightly varied names, phone formats (`+91 98200...` vs `98200...`), or missing email addresses. When commercial sales split across multiple IDs, account managers cannot see that a customer qualifies for bulk tier discounts or is experiencing churn risk.
4. **Header-versus-Line Discrepancies:** Accounting software updates order headers without recalculating underlying item lines, or applies discounts only at the footer. In the benchmark dataset, 1,312 orders exhibit discrepancy between stated order totals and line-item sums.
5. **Threshold Blind Spots:** Inventory snapshot exports arrive with unpopulated reorder thresholds for new or transferred SKUs. Without automated imputation rules, zero replenishment alerts are triggered, leading to sudden out-of-stock events on high-velocity goods.

---

## 3. Target Audience: When Does a Pipeline Matter?

InsightFlow is engineered for:
- **Multi-Location Retailers & Distributors:** Organizations managing recurring sales, replenishment, and supplier catalogs across multiple branch warehouses.
- **Commercial Finance & Category Analysts:** Teams responsible for SKU rationalization, price elasticity modeling, and gross margin protection who currently waste hours manually reconciling spreadsheet formulas.
- **BI & Analytics Engineering Teams:** Developers tasked with replacing fragile spreadsheet workflows with version-controlled, tested, and containerized data pipelines.

> **Appropriate Scope Boundary:** A small single-store business with a single cash register and 50 transactions per week is better served by a well-structured spreadsheet. InsightFlow is designed for environments where data originates from multiple disparate systems, arrives repeatedly, and requires traceable audit gates before numbers reach executive stakeholders.

---

## 4. System Architecture & Data Flow

InsightFlow implements an 8-stage data lifecycle separating raw ingestion, pipeline assurance, relational storage, and analytical consumption:

```
[Raw Files: 3 XLSX, 5 CSV] 
       │
       ▼
[Stage 1: Ingestion & Text Profiling] ──> logs missing cells, type distributions, source row IDs
       │
       ▼
[Stage 2: Deterministic Hygiene Gates] ──> regex date parsing, currency extraction, ID standardisation
       │
       ▼
[Stage 3: Business Validation & Quarantine] ──> duplicate elimination, outlier capping, price-swap repair
       │                                     └──> data/processed/rejected/ (*_rejected.csv)
       ▼
[Stage 4: Relational Star Schema (PostgreSQL 16)]
       ├── 8 Physical Tables (PK, FK, CHECK constraints, 10 B-tree indexes)
       └── 6 Standardized Analytical Views (vw_fact_sales, vw_fact_inventory, vw_customer_segments)
       │
       ├───> [FastAPI REST Service] ──> 6 validated analytical endpoints (Pydantic models)
       ├───> [SQL Analytics Suite] ──> 17 standalone analytical queries (CTEs, Window functions)
       ├───> [Streamlit Demo App] ──> In-memory Pandas pipeline, scenario simulator, audit matrices
       ├───> [Power BI Project (PBIP)] ──> TMDL semantic model, 27 DAX measures, 4 report pages
       └───> [Excel Assurance Workpaper] ──> openpyxl-generated audit model with dynamic formulas
```

### Core Architecture Components

| Component | Technology | Primary Function in Problem Resolution |
|---|---|---|
| **Pipeline Core** | Python 3.11+, pandas, NumPy | Profiles raw text, applies domain cleaning rules, enforces quarantine boundaries. |
| **Relational Store** | PostgreSQL 16, SQLAlchemy 2 | Enforces referential integrity, foreign keys, check constraints, and canonical view logic. |
| **Service Layer** | FastAPI, Pydantic v2, Uvicorn | Exposes type-safe, validated analytical endpoints with OpenAPI documentation. |
| **Interactive UI** | Streamlit, Plotly Express | Delivers an immediate browser workspace with price elasticity simulation and inventory review queues. |
| **Enterprise BI** | Power BI (`.pbip`), TMDL, PBIR | Version-controlled semantic model with 27 DAX measures and 4 executive report pages. |
| **Audit Workpaper** | Excel (`.xlsx`), openpyxl | Generates corporate data assurance models with dynamic formulas and formula-injection guards. |
| **Test Suite** | pytest, httpx, Ruff | 240 automated tests covering unit math, schema constraints, and semantic model structure. |

---

## 5. Decision Use Cases & Analytical Evidence

InsightFlow is structured around four concrete retail decision workflows:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. SKU MARGIN INVESTIGATION & PRICE SENSITIVITY SIMULATION                                            │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ • Business Question : Which high-turnover products destroy margin, and what pricing adjustment protects│
│                       profit without triggering catastrophic demand collapse?                          │
│ • Analytical Evidence: Basmati Rice 5kg (P0010) generates ₹1.65 Cr in gross revenue (#1 seller) but   │
│                       yields an anemic 2.15% margin (₹354K profit) vs company average of 20.3%.       │
│ • Decision Supported : Dynamic sensitivity simulator models a +3.0% price increase; formula proves a  │
│                       58.3% break-even volume drop buffer before baseline profit is compromised.       │
│ • Operational Caveat : Elasticity parameters are user-configured scenario inputs, not econometric proofs│
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 2. WORKING CAPITAL REPLENISHMENT PRIORITIZATION                                                        │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ • Business Question : Which SKU-location positions face stockout risk, and how much working capital is │
│                       required to restore buffer stock?                                                │
│ • Analytical Evidence: Out of 449 positions, 40 are out of stock (0 units) and 56 are below reorder   │
│                       thresholds. Restoring safety stock requires ₹966,026.68 in purchase cost.        │
│ • Decision Supported : Generates prioritized purchase order queues sorted by lead-time runout urgency,│
│                       preventing stockout exposure across ₹1.34M in catalog retail valuation.         │
│ • Operational Caveat : Snapshot stock does not capture intra-month receipts; suggested orders are not  │
│                       stochastic demand forecasts.                                                     │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. CUSTOMER IDENTITY CONSOLIDATION & WHOLESALE CONCENTRATION                                          │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ • Business Question : How dependent is revenue on top commercial accounts, and are credit limits      │
│                       compromised by split customer accounts?                                          │
│ • Analytical Evidence: 40 customers registered twice; deterministic entity resolution unified 210     │
│                       orders and ₹5.87M into primary wholesale profiles (e.g. Kapoor, Desai, Shah).    │
│ • Decision Supported : Restores accurate customer LTV; confirms wholesale concentration at 91.8% of    │
│                       turnover and true repeat purchase rate at 82.6% (vs 81.6% unmapped).            │
│ • Operational Caveat : Remapping relies on strict matching of email or name+phone; unlinked records    │
│                       remain separate accounts.                                                        │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. DATA DEFECT TO DECISION IMPACT ASSURANCE                                                           │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ • Business Question : What is the financial and operational risk of relying on raw unvalidated feeds? │
│ • Analytical Evidence: Raw line items overstate turnover by +105.7% (₹429.93M); unverified headers     │
│                       create a ₹5.72M ledger variance; swapped SKU prices cause a false -₹2.87M loss.  │
│ • Decision Supported : Enforces automated quarantine and line-level recalculation before figures enter │
│                       general ledger postings or executive briefings.                                  │
│ • Operational Caveat : Verified on synthetic retail benchmark; real deployment requires client rule    │
│                       calibration.                                                                     │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Empirical Verification & Defect-to-Decision Audit Findings

The following figures are directly reproducible from the codebase by running `python scripts/run_defect_impact.py`:

### Table 1: Sales Turnover & Order Volume Reconciliation

| Metric Dimension | Unvalidated (Raw Lines) | Unvalidated (Raw Headers) | Validated Ground Truth | Distortion Removed / Root Cause |
|---|---|---|---|---|
| **Completed Net Revenue** | ₹429,933,374.74 | ₹214,754,964.09 | **₹209,034,798.31** | **+₹220.90M (+105.7%)** line inflation removed (75 quantity outliers, 117 decimal shifts, 391 duplicate rows) |
| **Completed Orders** | 35,541 lines | 8,172 orders | **7,878 orders** | **+294 phantom orders (+3.7%)** eliminated (107 duplicate orders, 187 quarantined orphans) |
| **Units Sold** | 2,233,511 units | Not tracked at header | **1,111,322 units** | **+1,122,189 units (+101.0%)** inflation quarantined (extreme outliers up to 25,000 units/line) |
| **Gross Margin %** | Wild volatility | Not tracked at header | **20.26%** | Swapped cost/price pairs on 3 SKUs repaired; prevented **-₹2.87M** false margin loss |

### Table 2: Customer Identity Fragmentation & Ghost Account Recovery

| Customer Metric | Unvalidated (Raw Data) | Validated Ground Truth | Variance Recovered | Operational Decision Consequence |
|---|---|---|---|---|
| **Active Buying Accounts** | 813 profiles | **780 profiles** | +33 ghost accounts unified | Eliminates fractured purchase history; restores true commercial tiers |
| **Customer Repeat Rate** | 81.5% | **82.6%** | -1.1% pts artificial dilution | Proves true customer retention across recurring wholesale buyers |
| **Split Order Volume** | 210 orders fragmented | **210 orders unified** | **₹5,873,460.12 consolidated** | Recovers accurate account balances for credit limit and rebate reviews |

*Top Accounts Restored from Duplicate Fragmented IDs:*
- **Kapoor Agencies (`C00201`):** 20 orders unified · **₹935,183.49** consolidated into primary account.
- **Desai Enterprises (`C00173`):** 20 orders unified · **₹901,793.51** consolidated into primary account.
- **Shah Distributors (`C00638`):** 22 orders unified · **₹891,355.37** consolidated into primary account.
- **Joshi Agencies (`C00404`):** 14 orders unified · **₹642,508.14** consolidated into primary account.
- **Joshi Traders (`C00237`):** 13 orders unified · **₹595,189.96** consolidated into primary account.

### Table 3: Inventory Replenishment & Threshold Assurance

| Inventory Parameter | Unvalidated Raw Feed | Validated Pipeline Ground Truth | Operational Decision Impact |
|---|---|---|---|
| **Threshold Coverage** | 96.1% (18 SKUs NULL) | **100.0% (0 NULL)** | Category median imputation restores automated replenishment triggers for 18 blind SKUs |
| **Stockout Positions** | 33 zero + 7 negative | **40 true stockout positions** | Flipped negative typing errors; verified physical stock levels |
| **Positions Below Reorder** | Incomplete (18 blind SKUs) | **96 active positions** | Surfaces actionable restocking needs across all warehouses |
| **Replenishment Capital** | Uncalculated | **₹966,026.68 (5,791 units)** | Allocates precise working capital at purchase cost to restore buffer stock |

---

## 7. Defect-to-Decision Traceability Matrix

Every data quality event logged by the pipeline is mapped to its downstream business consequence:

| Defect Category | Source Entity | Volume Detected | Pipeline Control Gate | Target Metric at Risk | Operational Consequence If Unvalidated |
|---|---|---|---|---|---|
| **Severe Quantity Outliers** | `order_items` | 75 rows | Quarantine & Reject (`qty > 1000`) | Net Revenue & Demand Velocity | Overstates turnover by 2.2x; triggers false production orders |
| **Misplaced Price Decimals** | `order_items` | 117 rows | Catalog List Price Fallback | Gross Margin & Unit Revenue | Causes 100x unit price swings; corrupts SKU margin rankings |
| **Inverted Cost/Price Pairs** | `products` | 3 SKUs | Value Comparison & Field Swap | Product Margin & SKU Retention | Creates false -₹2.87M loss; risks wrongful product delisting |
| **Split Customer Identity** | `customers` | 40 cust / 210 orders | Deterministic Entity Matching | Customer LTV & Repeat Rate | Fractures ₹5.87M across ghost IDs; understates account purchasing tier |
| **Header vs Line Mismatch** | `orders` | 1,312 orders | Line-Item Ground Truth Recalculation | General Ledger Reconciliation | Produces ₹5.72M unexplained variance between invoices and lines |
| **Missing Reorder Thresholds**| `inventory` | 18 SKUs | Category Median Imputation | Stockout Prevention & Restock POs | Leaves 18 SKUs without replenishment alerts; causes silent stockouts |
| **Exact Duplicate Rows** | `orders/items/inv`| 512 rows | Deduplication & Row Purge | Total Volume & Turnover | Double-counts orders and inflates order volume by 3.7% |

---

## 8. Verified Runtime Evidence & Visual Quality

Authentic browser captures generated by `scripts/validate_runtime_ui.py` running against the synthetic benchmark:

| Executive Overview | Sales & Products Performance |
|---|---|
| ![Executive Overview](screenshots/runtime/01_executive_overview.png) | ![Sales & Products](screenshots/runtime/02_sales_and_products.png) |
| *High-level commercial turnover (₹20.90 Cr), margin trajectories, regional sales.* | *Product scatter analysis, category margin distributions, SKU drilldowns.* |
| **Price & Margin Sensitivity Simulator** | **Inventory Intelligence & Capital Allocation** |
| ![Price Sensitivity Simulator](screenshots/runtime/02_price_sensitivity_simulator.png) | ![Inventory Intelligence](screenshots/runtime/03_inventory_intelligence.png) |
| *Basmati Rice P0010 case study: 58.3% break-even volume decline buffer.* | *Stock position health mix, replenishment capital (₹9.66 L), priority review queue.* |
| **Customers & Data Quality Assurance** | **Power BI Desktop Version-Controlled PBIP** |
| ![Customers & Data Quality](screenshots/runtime/04_customers_and_data_quality.png) | ![Semantic Model Architecture](screenshots/Semantic%20Model%20Architecture.png) |
| *Empirical defect impact comparison, ghost account recovery, quality logs.* | *Single-direction star schema, 27 implemented DAX measures, 100% key coverage.* |

---

## 9. How to Run and Reproduce

### Quickstart A: Interactive Streamlit Dashboard (No Database Required)

```bash
# 1. Clone repository
git clone https://github.com/meetpokal1/InsightFlow.git
cd InsightFlow

# 2. Create and activate virtual environment
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch interactive dashboard
streamlit run streamlit_app.py
```

### Quickstart B: Run Data Defect & Decision Impact CLI Audit

```bash
# Generates the complete terminal audit report comparing unvalidated vs validated metrics
python scripts/run_defect_impact.py
```

### Quickstart C: Full PostgreSQL Pipeline & API Backend

```bash
# Option 1: Docker Compose (Automated containerized PostgreSQL + Data Seeding + API)
docker compose up --build

# Option 2: Local PostgreSQL
# Set credentials in .env (see .env.example)
python scripts/run_pipeline.py --as-of 2026-09-30 --reset-schema
python scripts/run_analytics.py
uvicorn api.main:app --reload
```

### Quickstart D: Automated Test Suite & Code Formatting

```bash
# Run self-contained tests (168 passed offline; 72 database integration tests run in CI)
python -m pytest

# Run Ruff linting and formatting verification
ruff check .
ruff format --check .
```

---

## 10. Engineering Quality & Project Structure

```
InsightFlow/
├── streamlit_app.py                 Interactive demo application (no database credentials required)
├── .streamlit/config.toml           Streamlit theme configuration and layout settings
├── Dockerfile                       FastAPI production container image
├── docker-compose.yml               Multi-container PostgreSQL 16 + FastAPI service environment
├── .github/workflows/tests.yml      GitHub Actions CI: provisions PostgreSQL, runs pipeline, executes 240 tests
├── pyproject.toml                   Ruff, Black, and pytest configurations
├── requirements.txt                 Pinned production and development dependencies
├── data/
│   ├── raw/                         8 raw corrupted CSV/XLSX files and data generation manifest
│   └── processed/                   Pipeline output directory (clean CSVs, rejected rows, quality logs)
├── src/
│   ├── ingestion/                   Raw table loader and text profiling engine
│   ├── cleaning/                    Table cleaners, regex parsers, validators, quarantine handlers
│   ├── database/                    PostgreSQL connection pool, schema builder, bulk copy loader
│   ├── analytics/
│   │   ├── defect_impact.py         Data defect to business decision impact calculation engine
│   │   ├── demo.py                  In-memory Pandas calculations and price sensitivity simulator
│   │   ├── queries.py               Bound parameter SQL query execution functions
│   │   └── runner.py                CLI SQL analytics execution runner
│   ├── synthetic/                   Synthetic data generator and corruption injector
│   ├── config.py                    Environment settings management
│   ├── pipeline.py                  End-to-end ETL orchestration module
│   └── tables.py                    Canonical column schemas, load orders, and constraint definitions
├── sql/
│   ├── schema/                      PostgreSQL DDL: tables, constraints, B-tree indexes, views
│   └── analytics/                   17 standalone production SQL analytical queries
├── api/
│   ├── routes/                      FastAPI route definitions for sales, inventory, and customers
│   ├── schemas/                     Pydantic v2 response contracts
│   └── main.py                      FastAPI application entry point
├── powerbi/
│   ├── InsightFlow.pbip             Version-controlled Power BI Project entry point
│   ├── InsightFlow.Report/          Fabric PBIR visual layer definitions and queryState bindings
│   ├── InsightFlow.SemanticModel/   Tabular model (model.bim), star schema, 27 implemented measures
│   └── data/                        Local CSV extracts generated for offline desktop loading
├── documentation/                   Architecture, data flow, ER diagrams, KPI definitions, workpapers
│   ├── data_assurance_workpaper.xlsx Corporate audit model with dynamic Excel reconciliation formulas
│   └── diagrams/                    Architecture and data flow diagrams
├── scripts/
│   ├── run_defect_impact.py         Standalone CLI runner for defect-to-decision impact analysis
│   ├── run_pipeline.py              Pipeline CLI runner with flags (--skip-db, --reset-schema)
│   ├── run_analytics.py             SQL analytics runner
│   ├── export_powerbi_data.py       Power BI CSV deliverable exporter
│   ├── generate_data_assurance_workpaper.py Excel audit workpaper generation script
│   └── validate_runtime_ui.py       Automated Playwright QA validation and screenshot capture
├── tests/                           240 automated unit, integration, and contract tests
│   ├── test_defect_impact.py        Unit tests for defect impact calculations and traceability
│   ├── test_pipeline.py             Data pipeline preservation and repair tests
│   ├── test_price_sensitivity.py    Price elasticity and break-even tolerance tests
│   ├── test_inventory_metrics.py    Inventory threshold and valuation tests
│   └── test_powerbi_deliverable.py  PBIP semantic model and DAX measure structure tests
└── screenshots/                     Genuine Power BI Desktop and Streamlit runtime captures
    └── runtime/                     Direct browser screenshots and automated QA test results JSON
```

---

## 11. Boundaries, Assumptions & Real-World Validation

### Current System Boundaries
- **Synthetic Data Boundary:** All transactions, entity names, and financial figures are generated from an audited synthetic benchmark. They prove pipeline mechanics and decision logic, not actual commercial earnings.
- **Cost History:** Product costs reflect the current snapshot price; historical purchase cost variance is not modeled in the synthetic dataset.
- **Inventory Point-in-Time:** Inventory reflects a single snapshot date (30 September 2026); stock turnover is calculated against snapshot capital rather than multi-month trailing averages.
- **Scenario Assumptions:** The price sensitivity simulator uses explicit user-specified price adjustments and demand elasticity assumptions. It is a decision-support heuristic, not a causal econometric proof.

### Steps to Validate on Authorized Real-World Retail Data
To apply InsightFlow to a production retailer's commercial data:
1. **Source Connection:** Replace CSV file polling with secure SFTP drops or direct read-only connector pipelines into the POS and ERP source databases.
2. **Catalog Rule Calibration:** Align product category hierarchies, tax head logic (e.g. GST/VAT splits), and supplier lead times with actual supplier contracts.
3. **Quarantine Triage Workflow:** Connect rejected row exports to an operational ticketing system (e.g. Jira or ServiceNow) so store managers can review and correct orphan customer and store codes.
4. **Historical Cost Ingestion:** Introduce a slowly changing dimension (SCD Type 2) table for product cost prices to enable historical margin tracking.
5. **Security & Governance:** Configure role-based access control (RBAC), database encryption at rest, and credential rotation before deploying beyond internal demo environments.

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
