"""Launch the Streamlit demo application and capture authentic high-resolution screenshots.

Uses Playwright with Microsoft Edge in headless mode.
Saves screenshots to screenshots/runtime/.
"""

import os
import pathlib
import subprocess
import time
import urllib.request

from playwright.sync_api import sync_playwright

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "screenshots" / "runtime"
PORT = 8522
URL = f"http://127.0.0.1:{PORT}"


def wait_for_server(url: str, timeout: int = 30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(1)
    return False


def capture_screenshots():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Start streamlit server
    cmd = [
        str(PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"),
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
        if not wait_for_server(URL, timeout=35):
            raise RuntimeError(f"Streamlit server did not become ready at {URL}")
        print("Streamlit server is ready. Launching headless browser...")

        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge", headless=True)
            context = browser.new_context(viewport={"width": 1440, "height": 950})
            page = context.new_page()

            # 1. Executive Overview
            print("Navigating to Executive Overview...")
            page.goto(URL, wait_until="networkidle")
            page.wait_for_timeout(3500)
            page.screenshot(path=str(OUTPUT_DIR / "01_executive_overview.png"), full_page=True)
            print("Captured 01_executive_overview.png")

            # 2. Sales & Products
            print("Navigating to Sales & Products...")
            page.click("text=Sales & Products")
            page.wait_for_timeout(3000)
            page.screenshot(path=str(OUTPUT_DIR / "02_sales_and_products.png"), full_page=True)
            print("Captured 02_sales_and_products.png")

            # Capture focused view of Price Sensitivity Simulator
            sim_header = page.locator("text=Price & Margin Sensitivity Simulator")
            if sim_header.count() > 0:
                sim_header.scroll_into_view_if_needed()
                page.wait_for_timeout(1000)
                page.screenshot(path=str(OUTPUT_DIR / "02_price_sensitivity_simulator.png"))
                print("Captured 02_price_sensitivity_simulator.png")

            # 3. Inventory Intelligence
            print("Navigating to Inventory Intelligence...")
            page.click("text=Inventory Intelligence")
            page.wait_for_timeout(3000)
            page.screenshot(path=str(OUTPUT_DIR / "03_inventory_intelligence.png"), full_page=True)
            print("Captured 03_inventory_intelligence.png")

            # 4. Customers & Data Quality
            print("Navigating to Customers & Data Quality...")
            page.click("text=Customers & Data Quality")
            page.wait_for_timeout(3000)
            page.screenshot(
                path=str(OUTPUT_DIR / "04_customers_and_data_quality.png"), full_page=True
            )
            print("Captured 04_customers_and_data_quality.png")

            browser.close()
            print("All screenshots captured successfully.")

    finally:
        print("Terminating Streamlit server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("Streamlit process terminated.")


if __name__ == "__main__":
    capture_screenshots()
