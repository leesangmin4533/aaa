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

# Local imports - 프로젝트 내부 모듈
from login.login_bgf import login_bgf
from utils.log_parser import extract_tab_lines
from utils.db_util import write_sales_data
from utils.log_util import create_logger

# Directory configuration
SCRIPT_DIR = Path(__file__).with_name("scripts")
CODE_OUTPUT_DIR = Path(__file__).with_name("code_outputs")
ALL_SALES_DB_FILE = "all_sales_data.db"

# Script file configuration
DEFAULT_SCRIPT = "auto_collect_mid_products.js"  # 자동 데이터 수집 스크립트
LISTENER_SCRIPT = "data_collect_listener.js"     # 데이터 수집 이벤트 리스너
NAVIGATION_SCRIPT = "navigation.js"              # 페이지 네비게이션 스크립트

# Logger used for both console and file output
log = create_logger("main")


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


def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_experimental_option("detach", True)
    caps = DesiredCapabilities.CHROME.copy()
    caps["goog:loggingPrefs"] = {"browser": "ALL"}
    for key, value in caps.items():
        options.set_capability(key, value)
    return webdriver.Chrome(service=Service(), options=options)


def run_script(driver: webdriver.Chrome, name: str) -> Any:
    path = SCRIPT_DIR / name
    if not path.exists():
        msg = f"script file not found: {path}"
        print(msg)
        log("run_script", "ERROR", msg)
        raise FileNotFoundError(msg)
    with open(path, "r", encoding="utf-8") as f:
        js = f.read()
    return driver.execute_script(js)


def wait_for_data(driver: webdriver.Chrome, timeout: int = 10) -> Any | None:
    """Wait for the __parsedData__ variable to be available on the window object."""
    try:
        return WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return window.__parsedData__ || null")
        )
    except Exception:
        return None


def wait_for_mix_ratio_page(driver: webdriver.Chrome, timeout: int = 10) -> bool:
    """중분류별 매출 구성비 화면의 그리드가 나타날 때까지 대기한다."""
    selector = "div[id*='gdList.body'][id*='cell_'][id$='_0:text']"
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        return True
    except Exception:
        return False





def _initialize_driver_and_login(cred_path: str | None) -> webdriver.Chrome | None:
    """Create and initialize the Chrome driver, then log in."""
    log("init", "INFO", "Initializing Chrome driver...")
    driver = create_driver()
    if not login_bgf(driver, credential_path=cred_path):
        log("login", "ERROR", "Login failed.")
        print("로그인 실패")
        driver.quit()
        return None
    log("login", "INFO", "Login successful.")
    return driver


def _navigate_and_prepare_collection(driver: webdriver.Chrome) -> bool:
    """Navigate to the target page for data collection."""
    log("navigation", "INFO", "Navigating to sales page...")
    run_script(driver, NAVIGATION_SCRIPT)
    if not wait_for_mix_ratio_page(driver):
        log("navigation", "ERROR", "Page load timed out.")
        print("페이지 로드 시간 초과")
        return False
    log("navigation", "INFO", "Successfully navigated to sales page.")
    return True


def _collect_data(driver: webdriver.Chrome) -> Any | None:
    """Run collection scripts and wait for the data."""
    log("collect", "INFO", "Starting data collection scripts...")
    run_script(driver, DEFAULT_SCRIPT)
    run_script(driver, LISTENER_SCRIPT)

    logs = driver.execute_script("return window.__midCategoryLogs__ || []")
    if logs:
        log("mid_category", "INFO", f"logs: {logs}")
        print("중분류 클릭 로그:", logs)

    parsed_data = wait_for_data(driver, 240)  # 240-second timeout
    if not parsed_data:
        log("collect", "ERROR", "Data collection timed out or failed.")
        print("데이터 수집 시간 초과 또는 실패")
        return None
    
    log("collect", "INFO", "Data collection complete.")
    return parsed_data


def _save_results(parsed_data: Any, date_str: str) -> None:
    """Save the collected data to DB."""
    if not isinstance(parsed_data, list) or not all(isinstance(item, str) for item in parsed_data):
        log("output", "ERROR", f"Invalid data format received: {type(parsed_data)}")
        print(f"잘못된 데이터 형식: {type(parsed_data)}")
        return

    db_path = CODE_OUTPUT_DIR / ALL_SALES_DB_FILE

    # Convert string data to list of dictionaries for DB insertion
    records_for_db = []
    for line in parsed_data:
        values = line.strip().split('\t')
        if len(values) == len(FIELD_ORDER):
            records_for_db.append(dict(zip(FIELD_ORDER, values)))
        else:
            log("db", "WARNING", f"Skipping malformed line for DB: {line}")

    # Save to DB
    if records_for_db:
        try:
            inserted = write_sales_data(records_for_db, db_path)
            log("db", "INFO", f"DB saved to {db_path}, inserted {inserted} rows")
            print(f"db saved to {db_path}, inserted {inserted} rows")
        except Exception as e:
            log("db", "ERROR", f"DB write failed: {e}")
            print(f"db write failed: {e}")
    else:
        log("db", "WARNING", "No valid records found to save to the database.")


def _handle_final_logs(driver: webdriver.Chrome) -> None:
    """Check for script errors and collect browser logs at the end."""
    # Check for script errors
    try:
        error = driver.execute_script("return window.__parsedDataError__ || null")
        if error:
            log("script", "ERROR", f"Script error: {error}")
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
            log("browser_log", "INFO", "Extracted log data:")
            print("추출된 로그 데이터:")
            for line in lines:
                log("browser_log", "INFO", line)
                print(line)
        else:
            log("browser_log", "INFO", "Browser console logs:")
            print("브라우저 콘솔 로그:")
            for entry in logs:
                log("browser_log", "INFO", str(entry))
                print(entry)
    except Exception as e:
        log("browser_log", "ERROR", f"Failed to collect browser logs: {e}")
        print(f"브라우저 로그 수집 실패: {e}")


def _run_collection_cycle() -> None:
    """
    Performs a single cycle of data collection and saving.
    """
    log("main", "INFO", "_run_collection_cycle started.")
    cred_path = os.environ.get("CREDENTIAL_FILE")
    driver = _initialize_driver_and_login(cred_path)
    if not driver:
        log("main", "ERROR", "Driver initialization or login failed. Skipping collection cycle.")
        return

    try:
        if not _navigate_and_prepare_collection(driver):
            log("main", "ERROR", "Navigation or preparation failed. Skipping collection cycle.")
            return

        date_str = datetime.now().strftime("%y%m%d")
        parsed_data = _collect_data(driver)
        
        if parsed_data:
            _save_results(parsed_data, date_str)
        else:
            log("main", "WARNING", "No parsed data collected. Skipping save results.")

        _handle_final_logs(driver)

    finally:
        log("main", "INFO", "Closing Chrome driver.")
        driver.quit()
        log("main", "INFO", "_run_collection_cycle finished.")


def main() -> None:
    """
    Main execution function: runs the browser, collects data, and saves it hourly.
    """
    while True:
        log("main", "INFO", "Starting new data collection cycle...")
        _run_collection_cycle()
        log("main", "INFO", "Data collection cycle finished. Waiting for 1 hour...")
        time.sleep(300) # Wait for 5 minutes
        log("main", "INFO", "1 hour wait completed. Starting next cycle.")

if __name__ == "__main__":
    main()