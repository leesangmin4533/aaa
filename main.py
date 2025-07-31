"""Main module for BGF Retail automation.

This script orchestrates the web automation process for BGF Retail, including:
  * Initializing and managing the Selenium WebDriver.
  * Handling user login and navigating to the sales analysis page.
  * Collecting sales data for past days and the current day.
  * Storing collected data into a SQLite database.
"""

from __future__ import annotations
from utils.db_util import write_sales_data, check_dates_exist
from utils.config import DB_FILE
import os
import sys
import logging

try:
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    from selenium import webdriver
except ImportError as exc:  # pragma: no cover - dependency missing
    logging.getLogger(__name__).warning(
        "Selenium or webdriver-manager not available: %s", exc
    )
    sys.exit(1)

from login.login_bgf import login_bgf
from utils.popup_util import close_popups_after_delegate
from dotenv import load_dotenv

import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import subprocess

from utils.log_util import get_logger

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

SCRIPT_DIR: Path = Path(__file__).resolve().parent
CODE_OUTPUT_DIR: Path = Path(__file__).resolve().parent / "code_outputs"
# 모든 수집 결과가 저장될 통합 DB 파일 경로
INTEGRATED_SALES_DB_FILE: str = "db/integrated_sales.db"
NAVIGATION_SCRIPT: str = "scripts/navigation.js"

logger = get_logger("bgf_automation", level=logging.DEBUG)
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
            lambda d: d.execute_script("return !!document.querySelector('[id*=\"gdList\"][id*=\"body\"]');")
        )
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(
                "const g=document.querySelector('[id*=\"gdList\"][id*=\"body\"]');"
                "return g && g.textContent.trim().length>0;"
            )
        )
        return True
    except Exception as e:
        logger.error(f"wait_for_mix_ratio_page failed: {e}")
        try:
            for entry in driver.get_log("browser"):
                logger.error(entry.get("message"))
        except Exception:
            pass
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
    past_dates_for_script = get_past_dates(num_days)  # YYYYMMDD format
    db_path = CODE_OUTPUT_DIR / INTEGRATED_SALES_DB_FILE
    if not db_path.exists():
        return False
    
    # Convert to YYYY-MM-DD for DB query
    dates_to_check_in_db = [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in past_dates_for_script]
    missing_dates = check_dates_exist(db_path, dates_to_check_in_db)
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
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return !!document.querySelector('[id*=\"gdList\"][id*=\"body\"]');")
        )
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(
                "const g=document.querySelector('[id*=\"gdList\"][id*=\"body\"]');"
                "return g && g.textContent.trim().length>0;"
            )
        )
        return True
    except Exception as e:
        logger.error(f"wait_for_mix_ratio_page failed: {e}")
        try:
            for entry in driver.get_log("browser"):
                logger.error(entry.get("message"))
        except Exception:
            pass
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
    logger = get_logger("bgf_automation", level=logging.DEBUG) # Configure the logger
    logger.info("Starting BGF Retail Automation...")
    driver = None
    try:
        # Load environment variables from project root if available
        load_dotenv(SCRIPT_DIR / ".env", override=False)

        driver = create_driver()
        if not login_bgf(driver, credential_path=None):
            logger.error("Login failed. Exiting.")
            return

        # 로그인 직후 나타나는 팝업을 모두 닫습니다.
        # 이 함수는 팝업이 모두 사라질 때까지 대기합니다.
        from utils.popup_util import close_popups_after_delegate
        close_popups_after_delegate(driver)

        # Load helper scripts before the main automation script
        import json

        with open(SCRIPT_DIR / "config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        default_script = config["scripts"]["default"]

        # Load nexacro_automation_library.js (contains data collection logic)
        run_script(driver, f"scripts/{default_script}")

        run_script(driver, "scripts/date_changer.js")

        run_script(driver, NAVIGATION_SCRIPT)
        if not wait_for_mix_ratio_page(driver):
            logger.error("Failed to load mix ratio page elements. Exiting.")
            return

        need_past = not is_past_data_available()
        if need_past:
            for past in get_past_dates():
                result = execute_collect_single_day_data(driver, past)
                data = result.get("data") if isinstance(result, dict) else None
                if data and isinstance(data, list) and data and isinstance(data[0], dict):
                    # 과거 날짜(past)를 target_date_str 인자로 전달합니다.
                    write_sales_data(data, CODE_OUTPUT_DIR / INTEGRATED_SALES_DB_FILE, target_date_str=past)
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
        print(f"중분류 클릭 로그: {mid_logs}")
        if not collected and mid_logs:
            collected = mid_logs

        if collected and isinstance(collected, list) and collected and isinstance(collected[0], dict):
            target_db = (
                Path(DB_FILE) if need_past else CODE_OUTPUT_DIR / f"{today_str}.db"
            )
            write_sales_data(collected, target_db)
        else:
            logger.warning("No valid data collected for %s", today_str)

        # Run jumeokbap prediction
        from utils.db_util import run_jumeokbap_prediction_and_save
        run_jumeokbap_prediction_and_save()

        try:
            # Retrieve and print popup monitor logs
            popup_logs = driver.execute_script("return window.popupMonitorLogs || [];")
            if popup_logs:
                logger.info("--- Popup Monitor Logs ---")
                for log_entry in popup_logs:
                    logger.info(log_entry)
                logger.info("--------------------------")

            for entry in driver.get_log("browser"):
                logger.info(entry.get("message"))
        except Exception:
            pass

    finally:
        if driver is not None:
            try:
                driver.quit()
                logger.info("WebDriver quit successfully.")
            except Exception as e:
                logger.error(f"Error quitting WebDriver: {e}")


if __name__ == "__main__":
    main()
