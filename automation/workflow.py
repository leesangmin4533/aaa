from __future__ import annotations

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

def get_past_dates(n: int = 7) -> list[str]:
    """YYYY-MM-DD 형식의 과거 날짜 리스트를 반환합니다."""
    dates = []
    today = datetime.now()
    for i in range(1, n + 1):
        d = today - timedelta(days=i)
        dates.append(d.strftime("%Y-%m-%d"))
    return dates


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
    run_script_fn: Callable[[Any, str], Any],
    wait_page_fn: Callable[[Any, int], bool],
    navigation_script: str,
    page_load_timeout: int,
) -> bool:
    log.info("Navigating to sales page...", extra={"tag": "navigation"})
    run_script_fn(driver, navigation_script)
    if not wait_page_fn(driver, page_load_timeout):
        log.error("Page load timed out.", extra={"tag": "navigation"})
        return False
    log.info("Successfully navigated to sales page.", extra={"tag": "navigation"})
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

    try:
        inserted = write_data_func(records_for_db, db_path, collected_at_override=collected_at_override)
        log.info(f"DB saved to {db_path}, inserted {inserted} new rows.", extra={"tag": "db"})
    except Exception as e:
        log.error(f"DB write failed: {e}", extra={"tag": "db"}, exc_info=True)


def _handle_final_logs(driver: Any) -> None:
    try:
        error = driver.execute_script("return window.automation && window.automation.error")
        if error:
            log.error(f"JavaScript error: {error}", extra={"tag": "script"})

        logs = driver.get_log("browser")
        log.info("--- Browser Console Logs ---", extra={"tag": "browser_log"})
        for entry in logs:
            log.info(str(entry), extra={"tag": "browser_log"})
        log.info("--- End of Browser Logs ---", extra={"tag": "browser_log"})

    except Exception as e:
        log.error(f"Failed to collect browser logs: {e}", extra={"tag": "browser_log"}, exc_info=True)


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
    navigation_script: str,
    automation_library_script: str,
    field_order: list[str],
    page_load_timeout: int,
) -> None:
    log.info(f"--- Starting collection cycle for {date_to_collect} ---", extra={"tag": "main"})
    driver = None
    try:
        driver = _initialize_driver_and_login(cred_path, create_driver_func, login_func)
        if not driver:
            return

        if not _navigate_and_prepare_collection(
            driver, run_script_func, wait_for_page_func, navigation_script, page_load_timeout
        ):
            return

        # window.nexacro 객체가 로드될 때까지 대기
        try:
            log.info("Waiting for window.nexacro object...", extra={"tag": "navigation"})
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return window.nexacro && typeof window.nexacro.getApplication === 'function' && window.nexacro.getApplication()")
            )
            log.info("window.nexacro object is ready.", extra={"tag": "navigation"})
        except TimeoutException:
            log.error("Timed out waiting for window.nexacro object.", extra={"tag": "navigation"})
            return
        
        run_script_func(driver, automation_library_script)
        
        # YYYY-MM-DD 형식을 YYYYMMDD로 변경하여 JS 함수에 전달
        date_yyyymmdd = date_to_collect.replace("-", "")
        result = collect_day_data_func(driver, date_yyyymmdd)

        if result and result.get("success"):
            parsed_data = result.get("data")
            if parsed_data:
                # 과거 날짜는 00:00, 오늘 날짜는 현재 시각으로 기록
                collected_at = f"{date_to_collect} 00:00" \
                    if date_to_collect != datetime.now().strftime("%Y-%m-%d") \
                    else datetime.now().strftime("%Y-%m-%d %H:%M")
                
                _process_and_save_data(parsed_data, db_path, field_order, write_data_func, collected_at_override=collected_at)
            else:
                log.warning(f"Collection for {date_to_collect} successful, but no data was returned.", extra={"tag": "main"})
        else:
            error_msg = result.get("message", "Unknown error") if result else "Unknown error"
            log.error(f"Collection script for {date_to_collect} failed: {error_msg}", extra={"tag": "main"})

        _handle_final_logs(driver)

    except Exception as e:
        log.critical(f"Critical error during collection cycle for {date_to_collect}: {e}", extra={"tag": "main"}, exc_info=True)
    finally:
        if driver:
            log.info(f"Closing driver for {date_to_collect} cycle.", extra={"tag": "main"})
            driver.quit()
        log.info(f"--- Finished collection cycle for {date_to_collect} ---", extra={"tag": "main"})
