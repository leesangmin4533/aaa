"""Main module for BGF Retail automation.

This script orchestrates the web automation process for BGF Retail, including:
  * Initializing and managing the Selenium WebDriver.
  * Handling user login and navigating to the sales analysis page.
  * Collecting sales data for past days and the current day.
  * Storing collected data into a SQLite database.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional
import sys

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

SCRIPT_DIR: Path = Path(__file__).resolve().parent
CODE_OUTPUT_DIR: Path = Path(__file__).resolve().parent / "code_outputs"
PAST7_DB_FILE: str = "db/integrated_sales.db"
NAVIGATION_SCRIPT: str = "scripts/navigation.js"

# -----------------------------------------------------------------------------
# Placeholder hooks
# -----------------------------------------------------------------------------

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

def create_driver() -> Any:
    """Create and return a Selenium WebDriver instance."""
    chromedriver_path = r"C:\Users\kanur\.cache\selenium\chromedriver\win64\138.0.7204.168\chromedriver.exe"
    
    service = Service(executable_path=chromedriver_path)
    options = Options()
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=service, options=options)
    return driver


from login.login_bgf import login_bgf





from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def wait_for_page_elements(driver: Any, timeout: int = 60) -> bool:
    """Wait for key elements on the '중분류 매출 구성비' page to be present.
    Specifically waits for the gdList body to appear.
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[id*='gdList.body']"))
        )
        return True
    except Exception as e:
        print(f"Error waiting for page elements: {e}")
        return False


from utils.db_util import write_sales_data, check_dates_exist

def execute_collect_single_day_data(driver: Any, date_str: str) -> dict:
    driver.execute_script(f"window.automation.runCollectionForDate('{date_str}')")
    collected = None
    for _ in range(60):  # Increased attempts to wait for data
        collected = driver.execute_script("return window.automation.parsedData || null")
        if collected:
            break
        time.sleep(0.5) # Wait a bit longer
    return {"success": bool(collected), "data": collected}


def get_past_dates(num_days: int = 2) -> list[str]:
    today = datetime.now()
    past_dates = []
    for i in range(1, num_days + 1):
        past_date = today - timedelta(days=i)
        past_dates.append(past_date.strftime("%Y%m%d"))
    return past_dates


def is_past_data_available(num_days: int = 2) -> bool:
    past_dates = get_past_dates(num_days)
    db_path = CODE_OUTPUT_DIR / PAST7_DB_FILE
    missing_dates = check_dates_exist(db_path, past_dates)
    return len(missing_dates) == 0


# -----------------------------------------------------------------------------
# Core functionality
# -----------------------------------------------------------------------------

def run_script(driver: Any, name: str) -> Any:
    script_path = Path(SCRIPT_DIR) / name
    if not script_path.exists():
        raise FileNotFoundError(f"JavaScript file not found: {script_path}")
    script_text = script_path.read_text(encoding="utf-8")
    return driver.execute_script(script_text)





def main() -> None:
    print("Starting BGF Retail Automation...")
    driver = None
    try:
        driver = create_driver()
        if not login_bgf(driver, credential_path=None):
            return

        
        
        # Load default script (index.js) to initialize window.automation
        import json
        with open(SCRIPT_DIR / "config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        default_script = config["scripts"]["default"]
        run_script(driver, f"scripts/{default_script}")

        run_script(driver, NAVIGATION_SCRIPT)
        if not wait_for_page_elements(driver):
            print("Failed to load mix ratio page elements. Exiting.")
            return
        

        need_past = not is_past_data_available(num_days=2)
        if need_past:
            for past in get_past_dates(num_days=2):
                result = execute_collect_single_day_data(driver, past)
                data = result.get("data") if isinstance(result, dict) else None
                if data:
                    write_sales_data(data, CODE_OUTPUT_DIR / PAST7_DB_FILE)
                time.sleep(0.1)

        today_str = datetime.now().strftime("%Y%m%d")
        result = execute_collect_single_day_data(driver, today_str)
        collected = result.get("data") if isinstance(result, dict) else None

        _browser_logs = driver.get_log("browser") # For debugging browser console logs
        mid_logs = driver.execute_script("return window.__midCategoryLogs__ || []") # Logs from JavaScript for mid-category clicks
        print("중분류 클릭 로그", mid_logs)

        if collected:
            db_path = CODE_OUTPUT_DIR / PAST7_DB_FILE
            write_sales_data(collected, db_path)
        else:
            return

        # Run jumeokbap.py after data collection
        jumeokbap_script_path = SCRIPT_DIR.parent / "food_prediction" / "jumeokbap.py"
        python_executable = sys.executable
        print(f"Running jumeokbap.py: {python_executable} {jumeokbap_script_path}")
        default_api.run_shell_command(command=f"\"{python_executable}\" \"{jumeokbap_script_path}\"", description="Run jumeokbap prediction script.")

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()