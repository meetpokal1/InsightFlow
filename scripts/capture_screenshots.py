import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = Path("screenshots/runtime")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

PAGES = [
    ("Executive Overview", SCREENSHOT_DIR / "01-executive-overview.png"),
    ("Sales & Products", SCREENSHOT_DIR / "02-sales-products.png"),
    ("Inventory Intelligence", SCREENSHOT_DIR / "03-inventory-intelligence.png"),
    ("Customers & Data Quality", SCREENSHOT_DIR / "04-customers-data-quality.png"),
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True,
        )
        context = browser.new_context(viewport={"width": 1600, "height": 1200})
        page = context.new_page()

        print("Navigating to running Streamlit application...")
        page.goto("http://localhost:8501", timeout=60000)

        page.wait_for_selector('[data-testid="stSidebar"]', timeout=60000)
        time.sleep(3)

        for page_name, out_path in PAGES:
            print(f"Testing and capturing page: {page_name}")
            radio_item = page.locator(f'[data-testid="stSidebar"] label:has-text("{page_name}")')
            radio_item.click()

            time.sleep(2)
            page.wait_for_selector(
                '[data-testid="stStatusWidget"]', state="detached", timeout=30000
            )
            time.sleep(2)

            page.screenshot(path=str(out_path), full_page=False)
            print(f"Saved: {out_path} ({out_path.stat().st_size} bytes)")

        browser.close()
        print("All four genuine runtime screenshots captured successfully!")


if __name__ == "__main__":
    main()
