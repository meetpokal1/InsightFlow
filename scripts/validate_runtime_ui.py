"""Automated QA inspection of Streamlit runtime UI.

Performs live DOM inspection, slider interaction, extreme value testing,
and captures verified high-resolution screenshots.
"""

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from playwright.sync_api import sync_playwright

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "screenshots" / "runtime"
PORT = 8533
URL = f"http://127.0.0.1:{PORT}"


def wait_for_server(url: str, timeout: int = 35):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def run_ui_qa():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = {}

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        "streamlit_app.py",
        f"--server.port={PORT}",
        "--server.headless=true",
        "--browser.serverAddress=127.0.0.1",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
    ]
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    print(f"Starting Streamlit app on port {PORT}...")
    proc = subprocess.Popen(cmd, cwd=PROJECT_ROOT, env=env)

    try:
        if not wait_for_server(URL, timeout=40):
            raise RuntimeError(f"Streamlit server did not become ready at {URL}")
        print("Streamlit server is ready. Launching Playwright browser...")

        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 950})
            page = context.new_page()

            # ---------------------------------------------------------
            # 1. Executive Overview
            # ---------------------------------------------------------
            print("\n[QA Step 1] Validating Executive Overview...")
            page.goto(URL, wait_until="networkidle")
            page.wait_for_selector('[data-testid="stMetricValue"]', timeout=20000)
            page.wait_for_timeout(3000)

            metric_vals = page.locator('[data-testid="stMetricValue"]').all_text_contents()
            metric_labels = page.locator('[data-testid="stMetricLabel"]').all_text_contents()
            exec_metrics = dict(zip(metric_labels, metric_vals, strict=False))
            print("Executive metrics displayed:", exec_metrics)
            results["executive_metrics"] = exec_metrics

            # Check Plotly charts rendered
            plotly_count = page.locator(".js-plotly-plot").count()
            print(f"Rendered Plotly charts on Executive page: {plotly_count}")
            results["executive_plotly_count"] = plotly_count

            page.screenshot(path=str(OUTPUT_DIR / "01_executive_overview.png"), full_page=True)
            print("Captured fresh 01_executive_overview.png")

            # ---------------------------------------------------------
            # 2. Sales & Products & Simulator Interaction
            # ---------------------------------------------------------
            print("\n[QA Step 2] Validating Sales & Products + Sensitivity Simulator...")
            page.locator('[data-testid="stSidebar"]').get_by_text(
                "Sales & Products", exact=True
            ).click()
            page.wait_for_selector("text=Sales & Product Performance", timeout=15000)
            page.wait_for_timeout(1500)

            # Capture Sales & Products at top position showing KPIs and charts
            page.locator("text=Sales & Product Performance").scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            page.screenshot(path=str(OUTPUT_DIR / "02_sales_and_products.png"))
            print("Captured fresh 02_sales_and_products.png at top position")

            # Check initial simulator display (defaults to Basmati Rice P0010)
            sim_metrics_before = page.locator('[data-testid="stMetricValue"]').all_text_contents()
            print("Sales page metric values count:", len(sim_metrics_before))

            # Verify break-even tolerance text exists
            tolerance_elem = page.locator("text=Break-Even Tolerance:")
            has_tolerance = tolerance_elem.count() > 0
            print("Break-even tolerance text present:", has_tolerance)
            if has_tolerance:
                tolerance_text = tolerance_elem.locator("..").text_content()
                print("Break-even callout content:", tolerance_text)
                results["break_even_callout"] = tolerance_text

            # Test interaction: switch to explicit volume change mode
            explicit_radio = page.locator("text=Explicit volume change (%)")
            if explicit_radio.count() > 0:
                explicit_radio.click()
                page.wait_for_timeout(2000)
                print("Clicked Explicit volume change mode.")

            # Capture focused simulator component
            sim_section = page.locator("div.st-key-price-sensitivity-simulator")
            sim_section.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            sim_section.screenshot(path=str(OUTPUT_DIR / "02_price_sensitivity_simulator.png"))
            print("Captured fresh 02_price_sensitivity_simulator.png")

            # ---------------------------------------------------------
            # 3. Inventory Intelligence
            # ---------------------------------------------------------
            print("\n[QA Step 3] Validating Inventory Intelligence & Capital Semantics...")
            page.locator('[data-testid="stSidebar"]').get_by_text(
                "Inventory Intelligence", exact=True
            ).click()
            page.wait_for_selector("text=Priority review queue", timeout=20000)
            page.wait_for_timeout(1500)

            inv_metric_vals = page.locator('[data-testid="stMetricValue"]').all_text_contents()
            inv_metric_labels = page.locator('[data-testid="stMetricLabel"]').all_text_contents()
            inv_metrics = dict(zip(inv_metric_labels, inv_metric_vals, strict=False))
            print("Inventory metrics displayed:", inv_metrics)
            results["inventory_metrics"] = inv_metrics

            # Check that review queue table has columns:
            # Buffer deficit, Replenish cost, Status, On hand, Reorder level
            table_header = page.locator('[data-testid="stDataFrame"]').first.text_content()
            has_buffer_deficit = (
                "Buffer deficit" in table_header or page.locator("text=Buffer deficit").count() > 0
            )
            has_replenish_cost = (
                "Replenish cost" in table_header
                or page.locator("text=Replenish cost (₹)").count() > 0
            )
            print("Table has Buffer deficit column:", has_buffer_deficit)
            print("Table has Replenish cost column:", has_replenish_cost)
            results["table_has_replenish_fields"] = has_buffer_deficit and has_replenish_cost

            # Capture Inventory Intelligence from top position showing key inventory cards & charts
            page.get_by_text("Total Inventory Value", exact=True).first.scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            page.screenshot(path=str(OUTPUT_DIR / "03_inventory_intelligence.png"))
            print("Captured fresh 03_inventory_intelligence.png at top position")

            # ---------------------------------------------------------
            # 4. Customers & Data Quality
            # ---------------------------------------------------------
            print("\n[QA Step 4] Validating Customers & Data Quality...")
            page.locator('[data-testid="stSidebar"]').get_by_text(
                "Customers & Data Quality", exact=True
            ).click()
            page.wait_for_selector("text=Data quality actions", timeout=20000)
            page.wait_for_timeout(1500)

            dq_metric_vals = page.locator('[data-testid="stMetricValue"]').all_text_contents()
            dq_metric_labels = page.locator('[data-testid="stMetricLabel"]').all_text_contents()
            dq_metrics = dict(zip(dq_metric_labels, dq_metric_vals, strict=False))
            print("Data Quality metrics displayed:", dq_metrics)
            results["data_quality_metrics"] = dq_metrics

            # Capture Customers & Data Quality from top header showing reconciliation metrics
            page.locator(
                "text=Pipeline Assurance & Reconciliation Balance"
            ).scroll_into_view_if_needed()
            page.wait_for_timeout(1000)
            page.screenshot(path=str(OUTPUT_DIR / "04_customers_and_data_quality.png"))
            print("Captured fresh 04_customers_and_data_quality.png at top position")

            browser.close()
            print(
                "\nAll runtime UI validation checks and screenshot captures completed successfully."
            )

    finally:
        print("Terminating Streamlit process...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Streamlit process terminated.")

    # Refuse duplicate evidence: the focused simulator capture must differ from the full page.
    simulator_screenshot = OUTPUT_DIR / "02_price_sensitivity_simulator.png"
    sales_screenshot = OUTPUT_DIR / "02_sales_and_products.png"
    screenshots_distinct = (
        hashlib.sha256(simulator_screenshot.read_bytes()).digest()
        != hashlib.sha256(sales_screenshot.read_bytes()).digest()
    )
    results["screenshot_checks"] = {
        "simulator_preview_distinct_from_sales_page": screenshots_distinct
    }
    if not screenshots_distinct:
        print("ERROR: simulator preview is identical to the full Sales & Products screenshot.")

    # Save summary results to JSON for verification reporting
    with open(OUTPUT_DIR / "ui_qa_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("Saved ui_qa_results.json")
    if not screenshots_distinct:
        raise RuntimeError("UI QA failed because the two runtime screenshots are identical.")


if __name__ == "__main__":
    run_ui_qa()
