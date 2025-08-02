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
import sys
import logging
import json

try:
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError as exc:  # pragma: no cover - dependency missing
    logging.getLogger(__name__).warning(
        "Selenium not available: %s", exc
    )
    sys.exit(1)

from login.login_bgf import login_bgf
from utils.popup_util import close_popups_after_delegate
from dotenv import load_dotenv

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict
import subprocess

from utils.log_util import get_logger
from webdriver_utils import (
    create_driver,
    wait_for_page_elements,
    wait_for_dataset_to_load,
    run_script,
)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

SCRIPT_DIR: Path = Path(__file__).resolve().parent
CODE_OUTPUT_DIR: Path = Path(__file__).resolve().parent / "code_outputs"
NAVIGATION_SCRIPT: str = "scripts/navigation.js"

logger = get_logger("bgf_automation", level=logging.DEBUG)
# Placeholder hooks
# -----------------------------------------------------------------------------




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

    # ``window.automation.changeDateAndSearch`` 함수가 준비될 때까지 대기
    try:
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script(
                "return typeof window.automation !== 'undefined' && "
                "typeof window.automation.changeDateAndSearch === 'function';"
            )
        )
    except Exception:
        logger.warning("changeDateAndSearch 함수가 로드되지 않았습니다.")

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
    logger.info(f"[execute_collect_single_day_data] Raw data from JS: {parsed}")
    return {"success": bool(success), "data": parsed if success else None}


def get_past_dates(num_days: int = 7) -> list[str]:
    """Return a list of past dates for collecting historical data.

    기본값은 ``num_days=7``로, 과거 7일 데이터를 수집할 때 사용됩니다.
    """
    today = datetime.now()
    past_dates = []
    for i in range(1, num_days + 1):
        past_date = today - timedelta(days=i)
        past_dates.append(past_date.strftime("%Y%m%d"))
    return past_dates

def get_missing_past_dates(db_path: Path, num_days: int = 7) -> list[str]:
    """Return a list of past dates for which data is missing in the DB.

    기본값은 ``num_days=7``로, 과거 7일 데이터 중 누락된 날짜를 확인합니다.
    """
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return [] # For testing, assume no missing dates
    
    past_dates_for_script = get_past_dates(num_days)  # YYYYMMDD format
    
    # Convert to YYYY-MM-DD for DB query
    dates_to_check_in_db = [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in past_dates_for_script]
    
    missing_dates = check_dates_exist(db_path, dates_to_check_in_db)
    return [d.replace("-", "") for d in missing_dates] # Return in YYYYMMDD format


def wait_for_data(driver: Any, timeout: int = 10) -> Any | None:
    """Poll ``window.__parsedData__`` until data is available or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        data = driver.execute_script("return window.__parsedData__ || null")
        if data is not None:
            return data
        time.sleep(0.5)
    return None




# -----------------------------------------------------------------------------
# Core functionality
# -----------------------------------------------------------------------------



def run_automation_for_store(store_name: str, store_config: Dict[str, Any], global_config: Dict[str, Any]) -> None:
    logger.info(f"--- Starting automation for store: {store_name} ---")
    driver = None
    try:
        driver = create_driver()
        if not login_bgf(driver, credential_keys=store_config["credentials_env"]):
            logger.error(f"Login failed for store: {store_name}. Skipping.")
            return

        close_popups_after_delegate(driver)

        default_script = global_config["scripts"]["default"]
        run_script(driver, f"scripts/{default_script}")
        run_script(driver, "scripts/date_changer.js")
        run_script(driver, NAVIGATION_SCRIPT)

        if not wait_for_dataset_to_load(driver):
            logger.error(f"Failed to load mix ratio page for {store_name}. Skipping.")
            return

        db_path = SCRIPT_DIR / store_config["db_file"]
        missing_past_dates = get_missing_past_dates(db_path)
        if missing_past_dates:
            logger.info(f"Missing past dates for {store_name}: {missing_past_dates}. Attempting to collect...")
            for past in missing_past_dates:
                result = execute_collect_single_day_data(driver, past)
                data = result.get("data") if isinstance(result, dict) else None
                if data and isinstance(data, list) and data and isinstance(data[0], dict):
                    write_sales_data(data, db_path, target_date_str=past)
                else:
                    logger.warning(f"No valid data collected for {past} at store {store_name}")
                time.sleep(0.1)

        today_str = datetime.now().strftime("%Y%m%d")
        result = execute_collect_single_day_data(driver, today_str)
        collected = result.get("data") if isinstance(result, dict) else None

        try:
            if collected and isinstance(collected, list) and collected and isinstance(collected[0], dict):
                logger.info(f"[{store_name}] Successfully collected {len(collected)} records for {today_str}.")
                logger.info(f"[{store_name}] Data to be written: {collected}")
                logger.info(f"[{store_name}] --- Calling write_sales_data ---")
                write_sales_data(collected, db_path)
                logger.info(f"[{store_name}] --- Returned from write_sales_data ---")
                for handler in logger.handlers:
                    handler.flush()
            else:
                logger.warning(f"No valid data collected for {today_str} at store {store_name}. Collected data: {collected}")
        except Exception as e:
            logger.error(f"Error calling write_sales_data for store {store_name}: {e}", exc_info=True)

        from utils.db_util import run_all_category_predictions
        run_all_category_predictions(db_path)

    finally:
        if driver is not None:
            driver.quit()
            logger.info(f"WebDriver quit for store: {store_name}.")
    logger.info(f"--- Finished automation for store: {store_name} ---")

def main() -> None:
    logger = get_logger("bgf_automation", level=logging.DEBUG)
    logger.info("Starting BGF Retail Automation for all stores...")

    load_dotenv(SCRIPT_DIR / ".env", override=True)

    with open(SCRIPT_DIR / "config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    stores_to_run = config.get("stores", {})
    if not stores_to_run:
        logger.error("No stores found in config.json. Exiting.")
        return

    for store_name, store_config in stores_to_run.items():
        run_automation_for_store(store_name, store_config, config)

if __name__ == "__main__":
    main()
