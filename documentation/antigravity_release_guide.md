# Antigravity release and screenshot runbook

This repository is prepared for a first public GitHub release. The Streamlit dashboard uses the included synthetic data and does not require PostgreSQL credentials. The PostgreSQL-backed API remains a separate local/Docker workflow.

## 1. Safety checks before publishing

1. Open this folder in Antigravity and inspect `README.md`, `.gitignore`, `.env.example`, `docker-compose.yml`, and `requirements.txt`.
2. Run `git status --short` and search for credentials or private data. Never commit `.env`, `.streamlit/secrets.toml`, API keys, local database files, real customer records, or unrelated machine files.
3. Confirm `data/raw/` contains only the included synthetic sample files.
4. Run the database-independent test subset and the full pipeline in skip-database mode (commands below). Do not run `docker compose down -v` unless you deliberately want to delete the local demo database volume.

## 2. Create and push the GitHub repository

Run in the project directory's terminal. The repository is intended to be public because it is a portfolio project and the included dataset is synthetic.

```powershell
gh auth status
```

If GitHub CLI is authenticated and `meetpokal1/InsightFlow` does not exist yet:

```powershell
git init
git branch -M main
git add .
git commit -m "Initial InsightFlow release"
gh repo create meetpokal1/InsightFlow --public --source . --remote origin --push
```

If the repository already exists, inspect it first instead of trying to create it again. Add the correct `origin` URL and push only after reviewing the staged file list:

```powershell
git remote -v
git status --short
git add .
git diff --cached --stat
git diff --cached
git commit -m "Prepare InsightFlow release"
git push -u origin main
```

If `gh auth status` fails, authenticate via `gh auth login` or create an empty repository in GitHub's web UI and then configure its remote. Do not paste access tokens into chat, source files, or screenshots.

## 3. Run and test the dashboard locally

Use Python 3.11+; the project was intended for Python 3.13. A virtual environment is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/run_pipeline.py --skip-db --as-of 2026-09-30
streamlit run streamlit_app.py
```

The dashboard should open at `http://localhost:8501`. All dashboard values are calculated from the included synthetic files, which pass through the project's ingestion, cleaning and validation pipeline. They are not real business results. The full `pytest` suite contains tests that require PostgreSQL; start the provided Docker Compose database or use the CI PostgreSQL service for the full suite.

## 4. Run runtime UI QA and capture genuine screenshots

Use the maintained QA-and-capture runner from the repository root. It starts Streamlit, checks the key interface content and interactions, and captures the runtime evidence in one pass.

```powershell
python -m pip install playwright
python scripts/validate_runtime_ui.py
```

The runner uses the active Python interpreter, requires Microsoft Edge to be installed, and writes these files to `screenshots/runtime/`:

- `01_executive_overview.png`
- `02_sales_and_products.png` — full Sales & Products page
- `02_price_sensitivity_simulator.png` — focused simulator view; verify this is visually distinct from the full-page capture
- `03_inventory_intelligence.png`
- `04_customers_and_data_quality.png`
- `ui_qa_results.json` — the metric and UI-validation evidence

Inspect each PNG after capture. The screenshots must come from the running app; never fabricate, retouch business values, or use placeholders to cover broken visuals. If a validation step fails, fix the application or the test selector and rerun the QA script rather than marking the release as passed.

## 5. Verify the Streamlit Community Cloud deployment

The repository README currently points to this Streamlit Community Cloud URL: https://insightflow-portfolio.streamlit.app/. Verify it in a normal browser and confirm the app is connected to the existing public repository. The dashboard runs from synthetic data without a database service or secrets. In Streamlit Community Cloud, the expected configuration is:

- Repository: `meetpokal1/InsightFlow`
- Branch: `main`
- Main file path: `streamlit_app.py`

After a change reaches the configured branch, verify the deployment finished and open the public URL. Test all four navigation pages, the core filters, and the price-sensitivity interaction in the hosted app. Keep hosted-app evidence distinct from local runtime screenshots. Do not claim the PostgreSQL-backed API or Power BI Desktop report is publicly deployed unless each is independently deployed and verified.

## 6. After the first release

- Confirm the GitHub Actions run is green. Fix real failures; do not disable tests just to get a green badge.
- Update this README with links to the verified hosted demo and genuine runtime screenshots.
- Power BI Desktop report pages and semantic model architecture are fully authored in `powerbi/InsightFlow.pbip` and captured in `screenshots/powerbi/`.
