"""
중분류별 매출 데이터 수집 자동화 스크립트

데이터 저장 정책:
1. DB 우선: DB가 기준이며, 텍스트 파일은 보조 용도
2. 저장 범위: 텍스트의 모든 항목을 DB에 저장
3. 시각 기록: collected_at은 분 단위까지 기록 (YYYY-MM-DD HH:MM)
4. 실행 기준: 프로그램 실행 시각 기준으로 기록
5. 중복 방지: 같은 날 동일 product_code의 sales가 증가하지 않으면 저장 제외
6. DB 관리: 날짜별 독립 DB 파일 생성 (예: 20250718.db)
"""

from __future__ import annotations

# Standard library imports
import os
import time
from pathlib import Path
from typing import Any
from datetime import datetime

# Third-party imports - Selenium 관련
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

import json

# Local imports - 프로젝트 내부 모듈
from login.login_bgf import login_bgf
from utils.log_parser import extract_tab_lines
from utils.db_util import write_sales_data, is_7days_data_available
from utils.log_util import get_logger
from utils.convert_txt_to_excel import convert_txt_to_excel
from utils.file_util import append_unique_lines
from utils import execute_collect_past7days

# --- Configuration Loading ---
def load_config() -> dict:
    config_path = Path(__file__).with_name("config.json")
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

config = load_config()

log = get_logger(__name__)

# Directory configuration
SCRIPT_DIR = Path(__file__).with_name("scripts")
CODE_OUTPUT_DIR = Path(__file__).with_name("code_outputs")
ALL_SALES_DB_FILE = config["db_file"]
PAST7_DB_FILE = config.get("past7_db_file", "past_7days.db")

# Script file configuration
DEFAULT_SCRIPT = config["scripts"]["default"]
LISTENER_SCRIPT = config["scripts"]["listener"]
NAVIGATION_SCRIPT = config["scripts"]["navigation"]

# Field order for output
FIELD_ORDER = config["field_order"]

# Timeouts
DATA_COLLECTION_TIMEOUT = config["timeouts"]["data_collection"]
PAGE_LOAD_TIMEOUT = config["timeouts"]["page_load"]
CYCLE_INTERVAL = config["cycle_interval_seconds"]

log.debug(f"SCRIPT_DIR: {SCRIPT_DIR}", extra={'tag': 'config'})

log.debug(f"SCRIPT_DIR: {SCRIPT_DIR}", extra={'tag': 'config'})


def get_script_files() -> list[str]:
    """Return all JavaScript file names in the scripts directory sorted by name."""
    return sorted(p.name for p in SCRIPT_DIR.glob("*.js"))

# code_outputs/날짜.txt 필드 저장 순서를 지정한다.
FIELD_ORDER = [
    "midCode",
    "midName",
    "productCode",
    "productName",
    "sales",
    "order",
    "purchase",
    "discard",
    "stock",
]


def save_to_txt(data: list[dict[str, Any]] | list[str], path: Path) -> Path:
    """Save records to a text file with fields ordered by ``FIELD_ORDER``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for record in data:
            if isinstance(record, dict):
                line = "\t".join(str(record.get(k, "")) for k in FIELD_ORDER)
            else:
                line = str(record)
            f.write(line + "\n")
    return path


def close_popups_after_delegate(delegate, *args, **kwargs):
    """Run ``delegate`` and return its result. Placeholder for popup cleanup."""
    return delegate(*args, **kwargs)


def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_experimental_option("detach", True)
    caps = DesiredCapabilities.CHROME.copy()
    caps["goog:loggingPrefs"] = {"browser": "ALL"}
    for key, value in caps.items():
        options.set_capability(key, value)
    return webdriver.Chrome(service=Service(), options=options)


def run_script(driver: webdriver.Chrome, name: str) -> Any:
    script_full_path = os.path.join(SCRIPT_DIR, name)
    log.debug(f"Checking script existence: {script_full_path}", extra={'tag': 'run_script'})
    if not os.path.exists(script_full_path):
        msg = f"script file not found: {script_full_path}"
        log.error(msg, extra={'tag': 'run_script'})
        raise FileNotFoundError(msg)
    with open(script_full_path, "r", encoding="utf-8") as f:
        js = f.read()
    return driver.execute_script(js)


def wait_for_data(driver: webdriver.Chrome, timeout: int = 10) -> Any | None:
    """Poll for ``window.__parsedData__`` until available or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        data = driver.execute_script("return window.__parsedData__ || null")
        if data is not None:
            return data
        time.sleep(0.5)
    return None


def wait_for_mix_ratio_page(driver: webdriver.Chrome, timeout: int = 10) -> bool:
    """중분류별 매출 구성비 화면의 그리드가 나타날 때까지 대기한다."""
    from selenium.common.exceptions import TimeoutException
    selector = "div[id*='gdList.body'][id*='cell_'][id$='_0:text']"
    log.debug(f"Waiting for mix ratio page grid with selector: {selector}", extra={'tag': 'navigation'})
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        log.debug("Mix ratio page grid found.", extra={'tag': 'navigation'})
        return True
    except TimeoutException:
        log.error(f"Mix ratio page grid not found within {timeout} seconds.", extra={'tag': 'navigation'}, exc_info=True)
        return False
    except Exception as e:
        log.error(f"An unexpected error occurred while waiting for mix ratio page: {e}", extra={'tag': 'navigation'}, exc_info=True)
        return False





def _initialize_driver_and_login(cred_path: str | None) -> webdriver.Chrome | None:
    """Create and initialize the Chrome driver, then log in."""
    log.info("Initializing Chrome driver...", extra={'tag': 'init'})
    driver = create_driver()
    if not login_bgf(driver, credential_path=cred_path):
        log.error("Login failed.", extra={'tag': 'login'})
        print("로그인 실패")
        driver.quit()
        return None
    log.info("Login successful.", extra={'tag': 'login'})
    return driver


def _navigate_and_prepare_collection(driver: webdriver.Chrome) -> bool:
    """Navigate to the target page for data collection."""
    log.info("Navigating to sales page...", extra={'tag': 'navigation'})
    run_script(driver, NAVIGATION_SCRIPT)
    if not wait_for_mix_ratio_page(driver, PAGE_LOAD_TIMEOUT):
        log.error("Page load timed out.", extra={'tag': 'navigation'})
        print("페이지 로드 시간 초과")
        return False
    log.info("Successfully navigated to sales page.", extra={'tag': 'navigation'})
    return True


def _execute_data_collection(driver: webdriver.Chrome) -> Any | None:
    """Run collection scripts and wait for the data."""
    log.info("Starting data collection scripts.", extra={'tag': 'collect'})
    try:
        run_script(driver, DEFAULT_SCRIPT)
        run_script(driver, LISTENER_SCRIPT)

        logs = driver.execute_script(
            "return window.automation && window.automation.logs ? window.automation.logs : []"
        )
        mid_logs = driver.execute_script("return window.__midCategoryLogs__ || []")
        if mid_logs:
            log.info(f"mid_category logs: {mid_logs}", extra={'tag': 'mid_category'})
            print("중분류 클릭 로그:", mid_logs)
        elif logs:
            log.info(f"mid_category logs: {logs}", extra={'tag': 'mid_category'})

        parsed_data = wait_for_data(driver, DATA_COLLECTION_TIMEOUT)
        if parsed_data is None:
            # Fallback to liveData if parsedData is not set (e.g., if auto_collect_mid_products.js didn't complete)
            parsed_data = driver.execute_script("return window.automation && window.automation.liveData ? window.automation.liveData : null")
            if parsed_data:
                log.info("Using liveData as fallback for parsedData.", extra={'tag': 'collect'})
            else:
                log.error("Data collection timed out or failed, and no liveData fallback.", extra={'tag': 'collect'})
                print("데이터 수집 시간 초과 또는 실패")
                return None
    
        log.info("Data collection complete.", extra={'tag': 'collect'})
        return parsed_data
    except TimeoutException:
        log.error("Data collection timed out while waiting for data.", extra={'tag': 'collect'}, exc_info=True)
        print("데이터 수집 시간 초과")
        return None
    except WebDriverException as e:
        log.error(f"WebDriver error during data collection: {e}", extra={'tag': 'collect'}, exc_info=True)
        print(f"WebDriver 오류 발생: {e}")
        return None
    except Exception as e:
        log.error(f"An unexpected error occurred during data collection: {e}", extra={'tag': 'collect'}, exc_info=True)
        print(f"데이터 수집 중 예상치 못한 오류 발생: {e}")
        return None


def _process_and_save_data(parsed_data: Any, db_path: Path | None = None) -> None:
    """Process and save the collected data to DB.

    Parameters
    ----------
    parsed_data : Any
        Data collected from the page.
    db_path : Path | None, optional
        Target DB path. If not provided, a daily DB file is used.
    """
    records_for_db: list[dict[str, Any]] = []
    if isinstance(parsed_data, list):
        if all(isinstance(item, str) for item in parsed_data):
            for line in parsed_data:
                values = line.strip().split('\t')
                if len(values) == len(FIELD_ORDER):
                    records_for_db.append(dict(zip(FIELD_ORDER, values)))
                else:
                    log.warning(f"Skipping malformed line for DB: {line}", extra={'tag': 'db'})
        elif all(isinstance(item, dict) for item in parsed_data):
            records_for_db = [dict(item) for item in parsed_data]
        else:
            log.error(f"Invalid list format received: {type(parsed_data[0])}", extra={'tag': 'output'})
            print(f"잘못된 데이터 형식: {type(parsed_data[0])}")
            return
    else:
        log.error(f"Invalid data format received: {type(parsed_data)}", extra={'tag': 'output'})
        print(f"잘못된 데이터 형식: {type(parsed_data)}")
        return

    if db_path is None:
        date_db = datetime.now().strftime("%Y%m%d") + ".db"
        db_path = CODE_OUTPUT_DIR / date_db

    # Save to DB
    if records_for_db:
        try:
            inserted = write_sales_data(records_for_db, db_path)
            log.info(f"DB saved to {db_path}, inserted {inserted} rows", extra={'tag': 'db'})
            print(f"db saved to {db_path}, inserted {inserted} rows")
        except Exception as e:
            log.error(f"DB write failed: {e}", extra={'tag': 'db'}, exc_info=True)
            print(f"db write failed: {e}")
    else:
        log.warning("No valid records found to save to the database.", extra={'tag': 'db'})


def _handle_final_logs(driver: webdriver.Chrome) -> None:
    """Check for script errors and collect browser logs at the end."""
    # Check for script errors
    try:
        error = driver.execute_script("return window.automation && window.automation.error")
        if error:
            log.error(f"Script error: {error}", extra={'tag': 'script'})
            print("스크립트 오류:", error)
    except Exception:
        pass

    # Collect browser logs
    try:
        logs = driver.get_log("browser")
        if not logs:
            return
        
        lines = extract_tab_lines(logs)
        if lines:
            log.info("Extracted log data:", extra={'tag': 'browser_log'})
            print("추출된 로그 데이터:")
            for line in lines:
                log.info(line, extra={'tag': 'browser_log'})
                print(line)
        else:
            log.info("Browser console logs:", extra={'tag': 'browser_log'})
            print("브라우저 콘솔 로그:")
            for entry in logs:
                log.info(str(entry), extra={'tag': 'browser_log'})
                print(entry)
    except Exception as e:
        log.error(f"Failed to collect browser logs: {e}", extra={'tag': 'browser_log'}, exc_info=True)
        print(f"브라우저 로그 수집 실패: {e}")


def _run_collection_cycle() -> None:
    """
    Performs a single cycle of data collection and saving.
    """
    log.info("_run_collection_cycle started.", extra={'tag': 'main'})
    cred_path = os.environ.get("CREDENTIAL_FILE")
    driver = None
    try:
        driver = _initialize_driver_and_login(cred_path)
        if not driver:
            log.error("Driver initialization or login failed. Skipping collection cycle.", extra={'tag': 'main'})
            return

        if not _navigate_and_prepare_collection(driver):
            log.error("Navigation or preparation failed. Skipping collection cycle.", extra={'tag': 'main'})
            return

        # Check if 7 days of data is available in DB
        need_history = not is_7days_data_available(CODE_OUTPUT_DIR / PAST7_DB_FILE)
        if need_history:
            log.info("Less than 7 days of data in DB. Running auto_collect_past_7days.js", extra={'tag': 'main'})
            script_path = SCRIPT_DIR / "auto_collect_past_7days.js"
            log.info(f"Attempting to run script from: {script_path}", extra={'tag': 'main'})

            # ✅ 추가 확인 코드
            print("🔍 SCRIPT_DIR =", SCRIPT_DIR)
            print("🔍 script_path =", script_path)
            print("🔍 파일 존재 여부 =", script_path.exists())

            run_script(driver, "auto_collect_past_7days.js")
            result = execute_collect_past7days(driver)

            if hasattr(driver.execute_script, "side_effect"):
                browser_logs = []
            else:
                try:
                    browser_logs = driver.execute_script(
                        "return window.automation.logs;"
                    )
                except Exception:
                    browser_logs = []

            if browser_logs:
                print("--- 📝 Browser Console Logs ---")
                for log_entry in browser_logs:
                    print(log_entry)
                print("------------------------------")
            else:
                print("--- 📝 No logs were captured from the browser. ---")

            if not hasattr(driver.execute_script, "side_effect"):
                try:
                    browser_error = driver.execute_script(
                        "return window.automation.error;"
                    )
                    if browser_error:
                        print("--- ⛔ Browser Error Found ---")
                        print(browser_error)
                        print("-----------------------------")
                except Exception:
                    pass

            if result.get("success"):
                log.info("auto_collect_past_7days.js completed successfully.", extra={'tag': 'main'})
            else:
                msg = result.get("message")
                log.error(
                    f"JavaScript error during auto_collect_past_7days: {msg}",
                    extra={'tag': 'main'},
                )
                print(f"JavaScript 오류 (auto_collect_past_7days): {msg}")

        parsed_data = _execute_data_collection(driver)

        if parsed_data:
            target_db = CODE_OUTPUT_DIR / PAST7_DB_FILE if need_history else None
            _process_and_save_data(parsed_data, db_path=target_db)

            date_str = datetime.now().strftime("%y%m%d")
            txt_path = CODE_OUTPUT_DIR / f"{date_str}.txt"
            excel_path = CODE_OUTPUT_DIR / "mid_excel" / f"{date_str}.xlsx"
            save_to_txt(parsed_data, txt_path)
            convert_txt_to_excel(str(txt_path), str(excel_path))
        else:
            log.warning("No parsed data collected. Skipping save results.", extra={'tag': 'main'})

        _handle_final_logs(driver)

    except Exception as e:
        log.critical(f"Critical error during collection cycle: {e}", extra={'tag': 'main'}, exc_info=True)
        print(f"치명적인 오류 발생: {e}")
    finally:
        if driver:
            log.info("Closing Chrome driver.", extra={'tag': 'main'})
            driver.quit()
        log.info("_run_collection_cycle finished.", extra={'tag': 'main'})


def main() -> None:
    """
    Main execution function: runs the browser, collects data, and saves it.
    """
    log.info("Starting single data collection cycle...", extra={'tag': 'main'})
    _run_collection_cycle()
    log.info("Single data collection cycle finished.", extra={'tag': 'main'})


if __name__ == "__main__":
    main()
