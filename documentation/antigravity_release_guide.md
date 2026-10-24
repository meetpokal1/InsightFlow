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

## 4. Capture genuine runtime screenshots

Use Antigravity's local browser controls against `http://localhost:8501`. These PNGs must be direct captures of the running Streamlit page—do not generate, repaint, or fabricate screenshots.

Save four files into `screenshots/runtime/`:

- `01-executive-overview.png`: headline metrics, monthly revenue, regional/category charts, inventory signals.
- `02-sales-products.png`: sales filters, monthly trend, margins and product performance.
- `03-inventory-intelligence.png`: inventory statuses, inventory value and the priority review queue.
- `04-customers-data-quality.png`: customer analysis, quality-action log and raw-data profile.

For each screenshot:

1. Wait until the page has fully rendered and charts have finished loading.
2. Keep the synthetic-data notice visible wherever possible.
3. Make sure labels, charts, and tables are legible at desktop size; a viewport around 1440 × 1000 is a good starting point.
4. Avoid cropping, retouching data, hiding application errors, or exposing personal/private information.
5. Inspect each PNG after saving it and confirm the exact file exists in `screenshots/runtime/`.

If a page fails to load, stop and debug the application instead of using a mockup as a substitute. Report the failed step and the error message.

## 5. Optional live demo deployment

The Streamlit dashboard is the simplest public demo because it runs from synthetic data without a database service or secrets. After the GitHub repo has been pushed, deploy it on Streamlit Community Cloud by selecting:

- Repository: `meetpokal1/InsightFlow`
- Branch: `main`
- Main file path: `streamlit_app.py`

Wait for the deployment build to finish, open the public URL, test all four navigation pages and the main filters, and capture screenshots from that hosted application only if the screens match the local run. Do not claim the backend API or Power BI report is publicly deployed unless it is independently deployed and tested.

## 6. After the first release

- Confirm the GitHub Actions run is green. Fix real failures; do not disable tests just to get a green badge.
- Update this README with links to the verified hosted demo and genuine runtime screenshots.
- Power BI Desktop report pages and semantic model architecture are fully authored in `powerbi/InsightFlow.pbip` and captured in `screenshots/powerbi/`.
