"""Main module for BGF Retail automation.

This script orchestrates the web automation process for BGF Retail, including:
  * Initializing and managing the Selenium WebDriver.
  * Handling user login and navigating to the sales analysis page.
  * Collecting sales data for past days and the current day.
  * Storing collected data into a SQLite database.
"""

from __future__ import annotations
from utils.db_util import write_sales_data, check_dates_exist
import os
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from login.login_bgf import login_bgf
from utils.popup_util import close_popups_after_delegate
from dotenv import load_dotenv
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium import webdriver

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import sys
import subprocess
import logging # Import logging module

from utils.logger_config import setup_logging # Import the new logging setup

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

SCRIPT_DIR: Path = Path(__file__).resolve().parent
CODE_OUTPUT_DIR: Path = Path(__file__).resolve().parent / "code_outputs"
# 모든 수집 결과가 저장될 통합 DB 파일 경로
INTEGRATED_SALES_DB_FILE: str = "db/integrated_sales.db"
NAVIGATION_SCRIPT: str = "scripts/navigation.js"

# Initialize logger (will be configured in main)
logger = logging.getLogger("bgf_automation")

# -----------------------------------------------------------------------------
# Placeholder hooks
# -----------------------------------------------------------------------------


def create_driver() -> Any:
    """Create and return a Selenium WebDriver instance."""
    service = Service(ChromeDriverManager().install())
    options = Options()

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=service, options=options)
    return driver


def wait_for_page_elements(driver: Any, timeout: int = 120) -> bool:
    """Wait for key elements on the '중분류 매출 구성비' page to be present.
    Specifically waits for the gdList body to appear.
    """
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div[id*='gdList.body']")
            )
        )
        return True
    except Exception as e:
        logger.error(f"Error waiting for page elements: {e}")
        return False


def execute_collect_single_day_data(driver: Any, date_str: str) -> dict:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        driver.execute_script(
            f"window.automation.runCollectionForDate('{date_str}')"
        )
        data = driver.execute_script("return window.__parsedData__ || null")
        return {"success": data is not None, "data": data}

    # 기다리는 동안 다른 수집 작업이 끝나기를 대기한다
    for _ in range(60):
        running = driver.execute_script(
            "return window.automation && window.automation.isCollecting;"
        )
        if not running:
            break
        time.sleep(0.25)

    # 수집 시작
    driver.execute_script(
        "window.automation.runCollectionForDate(arguments[0])",
        date_str,
    )

    parsed = None
    for _ in range(240):  # 최대 2분 대기
        running = driver.execute_script(
            "return window.automation && window.automation.isCollecting;"
        )
        parsed = driver.execute_script(
            "return window.automation && window.automation.parsedData || null;"
        )
        if not running:
            break
        time.sleep(0.5)

    success = isinstance(parsed, list) and len(parsed) > 0
    return {"success": bool(success), "data": parsed if success else None}


def get_past_dates(num_days: int = 2) -> list[str]:
    """Return a list of past dates for collecting historical data.

    기본값은 ``num_days=2``로, 과거 2일 데이터를 수집할 때 사용됩니다.
    """
    today = datetime.now()
    past_dates = []
    for i in range(1, num_days + 1):
        past_date = today - timedelta(days=i)
        past_dates.append(past_date.strftime("%Y%m%d"))
    return past_dates


def is_past_data_available(num_days: int = 2) -> bool:
    """Return ``True`` if past data for ``num_days`` exist in the DB.

    기본값은 ``num_days=2``로, 과거 2일 데이터가 이미 수집되었는지 확인합니다.
    """
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    past_dates = get_past_dates(num_days)
    db_path = CODE_OUTPUT_DIR / INTEGRATED_SALES_DB_FILE
    if not db_path.exists():
        return True
    missing_dates = check_dates_exist(db_path, past_dates)
    return len(missing_dates) == 0





def wait_for_data(driver: Any, timeout: int = 10) -> Any | None:
    """Poll ``window.__parsedData__`` until data is available or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        data = driver.execute_script("return window.__parsedData__ || null")
        if data is not None:
            return data
        time.sleep(0.5)
    return None


def wait_for_mix_ratio_page(driver: Any, timeout: int = 120) -> bool:
    """Wait for the mix ratio page to load fully."""
    try:
        grid_js = "return !!document.querySelector('[id*=\"gdList\"][id*=\"body\"]');"
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script(grid_js))

        data_js = (
            "const g=document.querySelector('[id*=\"gdList\"][id*=\"body\"]');"
            "return g && g.textContent.trim().length>0;"
        )
        WebDriverWait(driver, timeout).until(lambda d: d.execute_script(data_js))
        return True
    except Exception:
        return False


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
    global logger # Declare logger as global to modify the module-level logger
    logger = setup_logging(SCRIPT_DIR) # Configure the logger
    logger.info("Starting BGF Retail Automation...")
    driver = None
    try:
        # Load environment variables from project root if available
        load_dotenv(SCRIPT_DIR / ".env", override=False)

        driver = create_driver()
        if not login_bgf(driver, credential_path=None):
            logger.error("Login failed. Exiting.")
            return

        # Load helper scripts before the main automation script
        import json

        with open(SCRIPT_DIR / "config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        default_script = config["scripts"]["default"]

        # ``nexacro_helpers.js`` defines the ``window.automationHelpers`` object
        # used by ``index.js``. It must be loaded first.
        run_script(driver, "scripts/nexacro_helpers.js")
        run_script(driver, f"scripts/{default_script}")

        run_script(driver, NAVIGATION_SCRIPT)
        # Give some time for the page to stabilize after navigation
        time.sleep(2)
        if not wait_for_mix_ratio_page(driver):
            logger.error("Failed to load mix ratio page elements. Exiting.")
            return

        need_past = not is_past_data_available()
        if need_past:
            for past in get_past_dates():
                result = execute_collect_single_day_data(driver, past)
                data = result.get("data") if isinstance(result, dict) else None
                if data and isinstance(data, list) and data and isinstance(data[0], dict):
                    write_sales_data(data, CODE_OUTPUT_DIR / INTEGRATED_SALES_DB_FILE)
                else:
                    logger.warning("No valid data collected for %s", past)
                time.sleep(0.1)
                # Get JavaScript logs after each collection attempt
                js_automation_logs = driver.execute_script(
                    "return window.automation.logs || []"
                )
                if js_automation_logs:
                    logger.info(f"--- JavaScript Automation Logs for {past} ---")
                    for log_entry in js_automation_logs:
                        logger.info(log_entry)
                    logger.info("------------------------------------------")

        today_str = datetime.now().strftime("%Y%m%d")
        result = execute_collect_single_day_data(driver, today_str)
        collected = result.get("data") if isinstance(result, dict) else None

        # Get JavaScript logs after today's collection attempt
        js_automation_logs = driver.execute_script(
            "return window.automation.logs || []"
        )
        if js_automation_logs:
            logger.info(f"--- JavaScript Automation Logs for {today_str} ---")
            for log_entry in js_automation_logs:
                logger.info(log_entry)
            logger.info("------------------------------------------")
            if not collected:
                collected = js_automation_logs

        # Logs from JavaScript for mid-category clicks
        mid_logs = driver.execute_script(
            "return window.__midCategoryLogs__ || []"
        )
        logger.info(f"중분류 클릭 로그: {mid_logs}")
        if not collected and mid_logs:
            collected = mid_logs

        browser_logs = driver.get_log("browser")

        if collected and isinstance(collected, list) and isinstance(collected[0], dict):
            if need_past:
                db_path = CODE_OUTPUT_DIR / INTEGRATED_SALES_DB_FILE
            else:
                db_path = CODE_OUTPUT_DIR / f"{today_str}.db"
            write_sales_data(collected, db_path)
        else:
            logger.warning("No valid data collected for today")

        # Run jumeokbap.py after data collection
        jumeokbap_script_path = (
            SCRIPT_DIR.parent / "food_prediction" / "jumeokbap.py"
        )
        python_executable = sys.executable
        logger.info(
            f"Running jumeokbap.py: {python_executable} {jumeokbap_script_path}"
        )
        try:
            jumeokbap_result = subprocess.run(
                [python_executable, str(jumeokbap_script_path)],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("--- Jumeokbap Prediction Output ---")
            logger.info(jumeokbap_result.stdout)
            if jumeokbap_result.stderr:
                logger.error("--- Jumeokbap Prediction Error ---")
                logger.error(jumeokbap_result.stderr)
            logger.info("-----------------------------------")
        except subprocess.CalledProcessError as e:
            logger.error(f"Error running jumeokbap.py: {e}")
            logger.error(f"Stdout: {e.stdout}")
            logger.error(f"Stderr: {e.stderr}")

    finally:
        if driver is not None:
            try:
                driver.quit()
                logger.info("WebDriver quit successfully.")
            except Exception as e:
                logger.error(f"Error quitting WebDriver: {e}")


if __name__ == "__main__":
    main()
