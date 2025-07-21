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
from datetime import datetime, timedelta

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

from utils.js_util import execute_collect_single_day_data

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




def get_script_files() -> list[str]:
    """Return all JavaScript file names in the scripts directory sorted by name."""
    return sorted(p.name for p in SCRIPT_DIR.glob("*.js"))










def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_experimental_option("detach", True)
    options.add_argument("--disk-cache-size=0") # Disable disk cache
    caps = DesiredCapabilities.CHROME.copy()
    caps["goog:loggingPrefs"] = {"browser": "ALL"}
    for key, value in caps.items():
        options.set_capability(key, value)
    driver = webdriver.Chrome(service=Service(), options=options)
    driver.set_script_timeout(3600) # Set script timeout to 3600 seconds (1 hour) for general operations
    driver.command_executor.set_timeout(3600) # Set command executor timeout to 3600 seconds (1 hour) for general operations
    return driver


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
    """Poll for ``window.automation.parsedData`` until available or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        data = driver.execute_script("return window.automation && window.automation.parsedData || null")
        if data is not None:
            return data
        time.sleep(0.5)
    return None


def wait_for_mix_ratio_page(driver: webdriver.Chrome, timeout: int = 60) -> bool:
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





def get_past_dates(n: int = 7) -> list[str]:
    dates = []
    today = datetime.now()
    for i in range(1, n + 1):
        d = today - timedelta(days=i)
        dates.append(d.strftime("%Y%m%d"))
    return dates

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
        driver.execute_script("window.automation.autoClickAllMidCodesAndProducts();") # Start initial data collection

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


def _process_and_save_data(parsed_data: Any, db_path: Path | None = None, collected_at_override: str | None = None, skip_sales_check: bool = False) -> None:
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
        db_path = CODE_OUTPUT_DIR / ALL_SALES_DB_FILE

    # Save to DB
    if records_for_db:
        try:
            inserted = write_sales_data(records_for_db, db_path, collected_at_override)
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

        parsed_data = _execute_data_collection(driver)

        # Check if 7 days of data is available in DB
        need_history = not is_7days_data_available(CODE_OUTPUT_DIR / PAST7_DB_FILE)
        if need_history:
            log.info("7일치 데이터베이스 기록이 없어 과거 데이터 수집을 시작합니다.", extra={'tag': '7day_collection'})
            script_name = "auto_collect_past_7days.js"
            script_path = SCRIPT_DIR / script_name
            
            # Set timeouts for 7-day collection (1 hour)
            driver.set_script_timeout(3600)
            driver.command_executor._client_config.timeout = 3600
            log.info("WebDriver script and command executor timeouts set to 3600 seconds for 7-day collection.", extra={'tag': '7day_collection'})

            try:
                log.info(f"과거 데이터 수집 스크립트 실행 시도: {script_path}", extra={'tag': '7day_collection'})
                if not script_path.exists():
                    log.error(f"스크립트 파일을 찾을 수 없습니다: {script_path}", extra={'tag': '7day_collection'})
                    raise FileNotFoundError(f"과거 데이터 수집 스크립트가 존재하지 않습니다: {script_path}")

                run_script(driver, script_name)
                log.info(f"'{script_name}' 스크립트 실행 완료.", extra={'tag': '7day_collection'})
                
                past_dates = get_past_dates(7)
                for date_str in past_dates:
                    log.info(f"-------------------- 과거 데이터 수집 중: {date_str} --------------------", extra={'tag': '7day_collection'})
                    try:
                        result = execute_collect_single_day_data(driver, date_str)
                        log.debug(f"과거 데이터 수집 결과 ({date_str}): {result}", extra={'tag': '7day_collection'})

                        if result and result.get("success"):
                            historical_data = result.get("data")
                            if historical_data:
                                log.info(f"{date_str}에 대해 {len(historical_data)}개의 과거 데이터 레코드를 수집했습니다.", extra={'tag': '7day_collection'})
                                _process_and_save_data(historical_data, db_path=(CODE_OUTPUT_DIR / ALL_SALES_DB_FILE), collected_at_override=datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d 00:00"), skip_sales_check=True)
                            else:
                                log.warning(f"{date_str}에 대한 과거 데이터 수집은 성공했으나, 수집된 데이터가 없습니다.", extra={'tag': '7day_collection'})
                        else:
                            msg = result.get("message", "알 수 없는 오류")
                            log.error(f"{date_str}에 대한 과거 데이터 수집에 실패했습니다: {msg}", extra={'tag': '7day_collection'})
                            raise RuntimeError(f"과거 데이터 수집 스크립트 '{script_name}' 실행 실패: {msg}")

                    except (WebDriverException, RuntimeError) as e:
                        log.critical(f"{date_str} 과거 데이터 수집 중 심각한 오류 발생: {e}", extra={'tag': '7day_collection'}, exc_info=True)
                        raise
                    except Exception as e:
                        log.critical(f"{date_str} 과거 데이터 수집 중 예상치 못한 오류 발생: {e}", extra={'tag': '7day_collection'}, exc_info=True)
                        raise RuntimeError(f"{date_str} 과거 데이터 수집 중 예상치 못한 오류: {e}")

                log.info("과거 7일 데이터 수집 완료.", extra={'tag': '7day_collection'})

            except (FileNotFoundError, WebDriverException, RuntimeError) as e:
                log.critical(f"과거 데이터 수집 중 심각한 오류 발생: {e}", extra={'tag': '7day_collection'}, exc_info=True)
                raise
            except Exception as e:
                log.critical(f"과거 데이터 수집 중 예상치 못한 오류 발생: {e}", extra={'tag': '7day_collection'}, exc_info=True)
                raise RuntimeError(f"과거 데이터 수집 중 예상치 못한 오류: {e}")
            finally:
                # Revert timeouts to original values (300 seconds)
                driver.set_script_timeout(300)
                driver.command_executor._client_config.timeout = 300
                log.info("WebDriver script and command executor timeouts reverted to 300 seconds.", extra={'tag': '7day_collection'})

        if parsed_data:
            _process_and_save_data(parsed_data, db_path=None)
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
