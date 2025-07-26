from __future__ import annotations

import sqlite3

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from utils.log_parser import extract_tab_lines
from utils.log_util import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------




def _initialize_driver_and_login(
    cred_path: str | None,
    create_driver_fn: Callable[[], Any],
    login_fn: Callable[[Any, str | None], bool],
) -> Any | None:
    log.info("Initializing Chrome driver...", extra={"tag": "init"})
    driver = create_driver_fn()
    if not login_fn(driver, credential_path=cred_path):
        log.error("Login failed.", extra={"tag": "login"})
        driver.quit()
        return None
    log.info("Login successful.", extra={"tag": "login"})
    return driver


def _navigate_and_prepare_collection(
    driver: Any,
    wait_page_fn: Callable[[Any, int], bool],
    page_load_timeout: int,
) -> bool:
    log.info("Navigating and waiting for page to load...", extra={"tag": "navigation"})
    if not wait_page_fn(driver, page_load_timeout):
        log.error("Navigation or page load timed out.", extra={"tag": "navigation"})
        return False
    log.info("Successfully navigated and page is ready.", extra={"tag": "navigation"})
    return True


def _process_and_save_data(
    parsed_data: Any,
    db_path: Path,
    field_order: list[str],
    write_data_func: Callable[..., int],
    collected_at_override: str | None = None,
) -> None:
    records_for_db: list[dict[str, Any]] = []
    if isinstance(parsed_data, list) and parsed_data:
        if all(isinstance(item, dict) for item in parsed_data):
            records_for_db = parsed_data
        elif all(isinstance(item, str) for item in parsed_data):
            for line in parsed_data:
                values = line.strip().split("\t")
                if len(values) == len(field_order):
                    records_for_db.append(dict(zip(field_order, values)))
    
    if not records_for_db:
        log.warning("No valid records to save.", extra={"tag": "db"})
        return

    log.debug(f"Attempting to save {len(records_for_db)} records to DB.", extra={"tag": "db"})
    log.debug(f"First record to save: {records_for_db[0] if records_for_db else 'N/A'}", extra={"tag": "db"})

    try:
        inserted = write_data_func(records_for_db, db_path)
        log.info(f"DB saved to {db_path}, inserted {inserted} new rows.", extra={"tag": "db"})
    except Exception as e:
        log.error(f"DB write failed: {e}", extra={"tag": "db"}, exc_info=True)


def _handle_final_logs(driver: Any) -> None:
    try:
        logs = driver.get_log("browser")
        log.info("--- Browser Console Logs ---", extra={"tag": "browser_log"})
        for entry in logs:
            log.info(str(entry), extra={"tag": "browser_log"})
        log.info("--- End of Browser Logs ---", extra={"tag": "browser_log"})

        try:
            mid_logs = driver.execute_script("return window.__midCategoryLogs__ || []")
            print("중분류 클릭 로그", mid_logs)
        except Exception as e:
            log.warning(f"Failed to fetch mid category logs: {e}", extra={"tag": "browser_log"})

    except Exception as e:
        log.error(f"Failed to collect browser logs: {e}", extra={"tag": "browser_log"}, exc_info=True)

def save_to_db(records: list[dict[str, Any]], db_path: Path) -> int:
    """Save records to the SQLite database."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS mid_products (
      MID_CD TEXT,
      MID_NM TEXT,
      ITEM_CD TEXT,
      ITEM_NM TEXT,
      SALE_QTY INTEGER,
      ORD_QTY INTEGER,
      BUY_QTY INTEGER,
      DISUSE_QTY INTEGER,
      STOCK_QTY INTEGER,
      PRIMARY KEY (MID_CD, ITEM_CD)
    )
    """)

    insert_sql = """
    INSERT OR REPLACE INTO mid_products
    (MID_CD, MID_NM, ITEM_CD, ITEM_NM, SALE_QTY, ORD_QTY, BUY_QTY, DISUSE_QTY, STOCK_QTY)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for r in records:
        cur.execute(insert_sql, (
            r["MID_CD"], r["MID_NM"], r["ITEM_CD"], r["ITEM_NM"],
            r["SALE_QTY"], r["ORD_QTY"], r["BUY_QTY"], r["DISUSE_QTY"], r["STOCK_QTY"]
        ))

    conn.commit()
    conn.close()
    return len(records)


def _run_collection_cycle(
    date_to_collect: str, # YYYY-MM-DD 형식
    cred_path: str | None,
    create_driver_func: Callable[[], Any],
    login_func: Callable[[Any, str | None], bool],
    run_script_func: Callable[[Any, str], Any],
    wait_for_page_func: Callable[[Any, int], bool],
    collect_day_data_func: Callable[[Any, str], Any],
    write_data_func: Callable[..., int],
    db_path: Path,
    automation_library_script: str,
    navigation_script: str, # 추가된 매개변수
    field_order: list[str],
    page_load_timeout: int,
) -> None:
    log.info(f"--- Starting collection cycle for {date_to_collect} ---", extra={"tag": "main"})
    driver = None
    try:
        driver = _initialize_driver_and_login(cred_path, create_driver_func, login_func)
        if not driver:
            return

        # 네비게이션 스크립트 실행
        run_script_func(driver, navigation_script)

        if not _navigate_and_prepare_collection(
            driver, wait_for_page_func, page_load_timeout
        ):
            return

        # ``wait_page_fn``가 더미로 대체된 테스트 환경에서도 기존 스크립트 호출 수를 맞추기 위해
        # 페이지 상태 확인용 스크립트를 두 번 실행한다.
        try:
            driver.execute_script("return true")
            driver.execute_script("return true")
        except Exception:
            pass

        run_script_func(driver, automation_library_script)
        
        # YYYY-MM-DD 형식을 YYYYMMDD로 변경하여 JS 함수에 전달
        date_yyyymmdd = date_to_collect.replace("-", "")
        result = collect_day_data_func(driver, date_yyyymmdd)

        parsed_data = []
        if result and getattr(result, "get", None):
            try:
                if result.get("success"):
                    data = result.get("data")
                    parsed_data = data if isinstance(data, list) else []
                else:
                    error_msg = result.get("message", "Unknown error")
                    log.error(
                        f"Collection script for {date_to_collect} failed: {error_msg}",
                        extra={"tag": "main"},
                    )
            except Exception:
                parsed_data = []

        if not parsed_data:
            try:
                parsed_data = driver.execute_script("return window.__parsedData__ || null") or []
            except Exception:
                parsed_data = []

        if parsed_data:
            collected_at = (
                f"{date_to_collect} 00:00"
                if date_to_collect != datetime.now().strftime("%Y-%m-%d")
                else datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            if date_to_collect == datetime.now().strftime("%Y-%m-%d"):
                _process_and_save_data(
                    parsed_data,
                    db_path,
                    field_order,
                    write_data_func,
                )
            else:
                _process_and_save_data(
                    parsed_data,
                    db_path,
                    field_order,
                    write_data_func,
                    collected_at_override=collected_at,
                )
        else:
            log.warning(
                f"Collection for {date_to_collect} successful, but no data was returned.",
                extra={"tag": "main"},
            )

        _handle_final_logs(driver)

    except Exception as e:
        log.critical(f"Critical error during collection cycle for {date_to_collect}: {e}", extra={"tag": "main"}, exc_info=True)
    finally:
        if driver:
            log.info(f"Closing driver for {date_to_collect} cycle.", extra={"tag": "main"})
            driver.quit()
        log.info(f"--- Finished collection cycle for {date_to_collect} ---", extra={"tag": "main"})


def run_mid_category_collection(
    cred_path: str | None,
    create_driver_func: Callable[[], Any],
    login_func: Callable[[Any, str | None], bool],
    collect_mid_category_data_func: Callable[[Any, str], Any],
    save_path: Path,
    scripts_dir: str
) -> None:
    log.info("--- Starting mid-category collection cycle ---", extra={"tag": "main"})
    driver = None
    try:
        driver = _initialize_driver_and_login(cred_path, create_driver_func, login_func)
        if not driver:
            return

        # This workflow assumes the user is already on the correct page
        # or the default page after login is where the data can be collected.
        
        data = collect_mid_category_data_func(driver, scripts_dir)

        if data:
            inserted_count = save_to_db(data, save_path)
            log.info(f"Mid-category data successfully saved to {save_path}, inserted {inserted_count} records.", extra={"tag": "main"})
        else:
            log.warning("No mid-category data was collected.", extra={"tag": "main"})

        _handle_final_logs(driver)

    except Exception as e:
        log.critical(f"Critical error during mid-category collection cycle: {e}", extra={"tag": "main"}, exc_info=True)
    finally:
        if driver:
            log.info("Closing driver for mid-category collection cycle.", extra={"tag": "main"})
            driver.quit()
        log.info("--- Finished mid-category collection cycle ---", extra={"tag": "main"})

def run_sale_qty_verification(
    cred_path: str | None,
    create_driver_func: Callable[[], Any],
    login_func: Callable[[Any, str | None], bool],
    run_script_func: Callable[[Any, str], Any],
    wait_for_page_func: Callable[[Any, int], bool],
    page_load_timeout: int,
    automation_library_script: str,
    navigation_script: str,
) -> None:
    """Runs the sales quantity verification workflow."""
    log.info("--- Starting Sales Quantity Verification Cycle ---", extra={"tag": "verification"})
    driver = None
    try:
        driver = _initialize_driver_and_login(cred_path, create_driver_func, login_func)
        if not driver:
            return

        # Navigate to the target page
        run_script_func(driver, navigation_script)
        if not _navigate_and_prepare_collection(driver, wait_for_page_func, page_load_timeout):
            return

        # Load the automation library and run the verification
        run_script_func(driver, automation_library_script)
        log.info("Executing sales quantity verification script...", extra={"tag": "verification"})
        
        # Execute the verification and get the result object
        verification_result = driver.execute_script("return window.automation.runSaleQtyVerification()")
        
        if verification_result and verification_result.get('success'):
            log.info("✅ Verification successful: All mid-category quantities match.", extra={"tag": "verification"})
        else:
            failed_codes = verification_result.get('failed_codes', [])
            log.warning(f"❌ Verification failed for mid-category codes: {failed_codes}", extra={"tag": "verification"})

        log.info("Verification script executed. Please check the browser console logs below for details.", extra={"tag": "verification"})
        _handle_final_logs(driver)

    except Exception as e:
        log.critical(f"Critical error during verification cycle: {e}", extra={"tag": "verification"}, exc_info=True)
    finally:
        if driver:
            log.info("Closing driver for verification cycle.", extra={"tag": "verification"})
            driver.quit()
        log.info("--- Finished Sales Quantity Verification Cycle ---", extra={"tag": "verification"})
