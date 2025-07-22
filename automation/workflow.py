from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from selenium.common.exceptions import TimeoutException, WebDriverException

from utils.log_parser import extract_tab_lines
from utils.log_util import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_past_dates(n: int = 7) -> list[str]:
    dates = []
    today = datetime.now()
    for i in range(1, n + 1):
        d = today - timedelta(days=i)
        dates.append(d.strftime("%Y%m%d"))
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
        print("로그인 실패")
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
        print("페이지 로드 시간 초과")
        return False
    log.info("Successfully navigated to sales page.", extra={"tag": "navigation"})
    return True


def _execute_data_collection(
    driver: Any,
    run_script_fn: Callable[[Any, str], Any],
    wait_data_fn: Callable[[Any, int], Any | None],
    default_script: str,
    listener_script: str,
    data_timeout: int,
) -> Any | None:
    log.info("Starting data collection scripts.", extra={"tag": "collect"})
    try:
        run_script_fn(driver, default_script)
        run_script_fn(driver, listener_script)
        driver.execute_script("window.automation.autoClickAllMidCodesAndProducts();")

        logs = driver.execute_script(
            "return window.automation && window.automation.logs ? window.automation.logs : []"
        )
        mid_logs = driver.execute_script("return window.__midCategoryLogs__ || []")
        if mid_logs:
            log.info(f"mid_category logs: {mid_logs}", extra={"tag": "mid_category"})
            print("중분류 클릭 로그:", mid_logs)
        elif logs:
            log.info(f"mid_category logs: {logs}", extra={"tag": "mid_category"})

        parsed_data = wait_data_fn(driver, data_timeout)
        if parsed_data is None:
            parsed_data = driver.execute_script(
                "return window.automation && window.automation.liveData ? window.automation.liveData : null"
            )
            if not parsed_data and mid_logs:
                parsed_data = mid_logs
            if parsed_data:
                log.info("Using liveData as fallback for parsedData.", extra={"tag": "collect"})
            else:
                log.error(
                    "Data collection timed out or failed, and no liveData fallback.",
                    extra={"tag": "collect"},
                )
                print("데이터 수집 시간 초과 또는 실패")
                return None

        log.info("Data collection complete.", extra={"tag": "collect"})
        return parsed_data
    except TimeoutException:
        log.error(
            "Data collection timed out while waiting for data.",
            extra={"tag": "collect"},
            exc_info=True,
        )
        print("데이터 수집 시간 초과")
        return None
    except WebDriverException as e:
        log.error(
            f"WebDriver error during data collection: {e}",
            extra={"tag": "collect"},
            exc_info=True,
        )
        print(f"WebDriver 오류 발생: {e}")
        return None
    except Exception as e:
        log.error(
            f"An unexpected error occurred during data collection: {e}",
            extra={"tag": "collect"},
            exc_info=True,
        )
        print(f"데이터 수집 중 예상치 못한 오류 발생: {e}")
        return None


def _process_and_save_data(
    parsed_data: Any,
    db_path: Path | None,
    field_order: list[str],
    code_output_dir: Path,
    all_sales_db_file: str,
    write_sales_data_fn: Callable[..., int],
    collected_at_override: str | None = None,
) -> None:
    records_for_db: list[dict[str, Any]] = []
    if isinstance(parsed_data, list):
        if all(isinstance(item, str) for item in parsed_data):
            for line in parsed_data:
                values = line.strip().split("\t")
                if len(values) == len(field_order):
                    records_for_db.append(dict(zip(field_order, values)))
                else:
                    log.warning(f"Skipping malformed line for DB: {line}", extra={"tag": "db"})
        elif all(isinstance(item, dict) for item in parsed_data):
            records_for_db = [dict(item) for item in parsed_data]
        else:
            log.error(f"Invalid list format received: {type(parsed_data[0])}", extra={"tag": "output"})
            print(f"잘못된 데이터 형식: {type(parsed_data[0])}")
            return
    else:
        log.error(f"Invalid data format received: {type(parsed_data)}", extra={"tag": "output"})
        print(f"잘못된 데이터 형식: {type(parsed_data)}")
        return

    if db_path is None:
        db_path = code_output_dir / all_sales_db_file

    if records_for_db:
        try:
            if collected_at_override is None:
                inserted = write_sales_data_fn(records_for_db, db_path)
            else:
                inserted = write_sales_data_fn(records_for_db, db_path, collected_at_override)
            log.info(f"DB saved to {db_path}, inserted {inserted} rows", extra={"tag": "db"})
            print(f"db saved to {db_path}, inserted {inserted} rows")
        except Exception as e:
            log.error(f"DB write failed: {e}", extra={"tag": "db"}, exc_info=True)
            print(f"db write failed: {e}")
    else:
        log.warning("No valid records found to save to the database.", extra={"tag": "db"})


def _handle_final_logs(
    driver: Any,
    code_output_dir: Path,
    append_lines_fn: Callable[[Path, list[str]], int],
    convert_fn: Callable[[str, str], Any],
) -> None:
    try:
        error = driver.execute_script("return window.automation && window.automation.error")
        if error:
            log.error(f"Script error: {error}", extra={"tag": "script"})
            print("스크립트 오류:", error)
    except Exception:
        pass

    try:
        logs = driver.get_log("browser")
        lines = extract_tab_lines(logs)
        if lines:
            log.info("Extracted log data:", extra={"tag": "browser_log"})
            print("추출된 로그 데이터:")
            for line in lines:
                log.info(line, extra={"tag": "browser_log"})
                print(line)
        else:
            log.info("Browser console logs:", extra={"tag": "browser_log"})
            print("브라우저 콘솔 로그:")
            for entry in logs:
                log.info(str(entry), extra={"tag": "browser_log"})
                print(entry)

        date_str = datetime.now().strftime("%y%m%d")
        txt_path = code_output_dir / f"{date_str}.txt"
        if lines:
            append_lines_fn(txt_path, lines)
        else:
            txt_path.parent.mkdir(parents=True, exist_ok=True)
            txt_path.touch(exist_ok=True)
        excel_path = code_output_dir / "mid_excel" / f"{date_str}.xlsx"
        convert_fn(str(txt_path), str(excel_path))
    except Exception as e:
        log.error(f"Failed to collect browser logs: {e}", extra={"tag": "browser_log"}, exc_info=True)
        print(f"브라우저 로그 수집 실패: {e}")


def _run_collection_cycle(
    cred_path: str | None,
    create_driver_fn: Callable[[], Any],
    login_fn: Callable[[Any, str | None], bool],
    run_script_fn: Callable[[Any, str], Any],
    wait_for_mix_ratio_page_fn: Callable[[Any, int], bool],
    wait_for_data_fn: Callable[[Any, int], Any | None],
    write_sales_data_fn: Callable[..., int],
    is_7days_available_fn: Callable[[Path], bool],
    append_lines_fn: Callable[[Path, list[str]], int],
    convert_fn: Callable[[str, str], Any],
    execute_collect_single_day_data_fn: Callable[[Any, str], Any],
    get_past_dates_fn: Callable[[int], list[str]],
    code_output_dir: Path,
    past7_db_file: str,
    all_sales_db_file: str,
    default_script: str,
    listener_script: str,
    navigation_script: str,
    field_order: list[str],
    page_load_timeout: int,
    data_timeout: int,
) -> None:
    log.info("_run_collection_cycle started.", extra={"tag": "main"})
    driver = None
    try:
        driver = _initialize_driver_and_login(cred_path, create_driver_fn, login_fn)
        if not driver:
            log.error("Driver initialization or login failed. Skipping collection cycle.", extra={"tag": "main"})
            return

        if not _navigate_and_prepare_collection(
            driver,
            run_script_fn,
            wait_for_mix_ratio_page_fn,
            navigation_script,
            page_load_timeout,
        ):
            log.error("Navigation or preparation failed. Skipping collection cycle.", extra={"tag": "main"})
            return

        parsed_data = _execute_data_collection(
            driver,
            run_script_fn,
            wait_for_data_fn,
            default_script,
            listener_script,
            data_timeout,
        )

        need_history = not is_7days_available_fn(code_output_dir / past7_db_file)
        if need_history:
            log.info("7일치 데이터베이스 기록이 없어 과거 데이터 수집을 시작합니다.", extra={"tag": "7day_collection"})
            driver.set_script_timeout(3600)
            driver.command_executor.set_timeout(3600)
            log.info(
                "WebDriver script and command executor timeouts set to 3600 seconds for 7-day collection.",
                extra={"tag": "7day_collection"},
            )
            try:
                run_script_fn(driver, "auto_collect_past_7days.js")
                past_dates = get_past_dates_fn(7)
                for date_str in past_dates:
                    log.info(
                        f"-------------------- 과거 데이터 수집 중: {date_str} -------------------",
                        extra={"tag": "7day_collection"},
                    )
                    result = execute_collect_single_day_data_fn(driver, date_str)
                    if result and result.get("success"):
                        historical_data = result.get("data")
                        if historical_data:
                            _process_and_save_data(
                                historical_data,
                                code_output_dir / past7_db_file,
                                field_order,
                                code_output_dir,
                                all_sales_db_file,
                                write_sales_data_fn,
                                collected_at_override=datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d 00:00"),
                            )
                        else:
                            log.warning(
                                f"{date_str}에 대한 과거 데이터 수집은 성공했으나, 수집된 데이터가 없습니다.",
                                extra={"tag": "7day_collection"},
                            )
                    else:
                        msg = result.get("message", "알 수 없는 오류") if result else "알 수 없는 오류"
                        log.error(
                            f"{date_str}에 대한 과거 데이터 수집에 실패했습니다: {msg}",
                            extra={"tag": "7day_collection"},
                        )
                        raise RuntimeError(f"과거 데이터 수집 스크립트 실행 실패: {msg}")
                log.info("과거 7일 데이터 수집 완료.", extra={"tag": "7day_collection"})
            finally:
                driver.set_script_timeout(300)
                driver.command_executor.set_timeout(300)
                log.info(
                    "WebDriver script and command executor timeouts reverted to 300 seconds.",
                    extra={"tag": "7day_collection"},
                )
            db_target = code_output_dir / past7_db_file
        else:
            db_target = code_output_dir / f"{datetime.now():%Y%m%d}.db"

        if parsed_data:
            _process_and_save_data(
                parsed_data,
                db_target,
                field_order,
                code_output_dir,
                all_sales_db_file,
                write_sales_data_fn,
            )
        else:
            log.warning("No parsed data collected. Skipping save results.", extra={"tag": "main"})

        _handle_final_logs(driver, code_output_dir, append_lines_fn, convert_fn)

    except Exception as e:
        log.critical(f"Critical error during collection cycle: {e}", extra={"tag": "main"}, exc_info=True)
        print(f"치명적인 오류 발생: {e}")
    finally:
        if driver:
            log.info("Closing Chrome driver.", extra={"tag": "main"})
            driver.quit()
        log.info("_run_collection_cycle finished.", extra={"tag": "main"})
