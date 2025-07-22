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

# Local imports - 프로젝트 내부 모듈
from login.login_bgf import login_bgf
from utils.db_util import write_sales_data, is_7days_data_available
from utils.log_util import get_logger

from utils.js_util import execute_collect_single_day_data

from utils.popup_util import close_popups_after_delegate

from automation.config import (
    SCRIPT_DIR,
    CODE_OUTPUT_DIR,
    ALL_SALES_DB_FILE,
    PAST7_DB_FILE,
    DEFAULT_SCRIPT,
    LISTENER_SCRIPT,
    NAVIGATION_SCRIPT,
    FIELD_ORDER,
    DATA_COLLECTION_TIMEOUT,
    PAGE_LOAD_TIMEOUT,
    CYCLE_INTERVAL,
)
from automation.driver import create_driver as _create_driver
from automation.scripts import (
    run_script as _run_script,
    wait_for_data as _wait_for_data,
    wait_for_mix_ratio_page as _wait_for_mix_ratio_page,
)
from automation.workflow import (
    get_past_dates as _get_past_dates,
    _initialize_driver_and_login as _wf_initialize_driver_and_login,
    _navigate_and_prepare_collection as _wf_navigate_and_prepare_collection,
    _execute_data_collection as _wf_execute_data_collection,
    _process_and_save_data as _wf_process_and_save_data,
    _handle_final_logs as _wf_handle_final_logs,
    _run_collection_cycle as _wf_run_collection_cycle,
)

log = get_logger(__name__)




def get_script_files() -> list[str]:
    """Return all JavaScript file names in the scripts directory sorted by name."""
    return sorted(p.name for p in SCRIPT_DIR.glob("*.js"))













def create_driver() -> Any:
    """Create and configure a Chrome WebDriver."""
    return _create_driver()


def run_script(driver: Any, name: str) -> Any:
    """Execute a JavaScript file located in :data:`SCRIPT_DIR`."""
    return _run_script(driver, name, SCRIPT_DIR)


def wait_for_data(driver: Any, timeout: int = 10) -> Any | None:
    """Wrapper around :func:`automation.scripts.wait_for_data`."""
    return _wait_for_data(driver, timeout)


def wait_for_mix_ratio_page(driver: Any, timeout: int = 60) -> bool:
    """Wrapper around :func:`automation.scripts.wait_for_mix_ratio_page`."""
    return _wait_for_mix_ratio_page(driver, timeout)





def get_past_dates(n: int = 7) -> list[str]:
    """Return list of date strings for the past ``n`` days."""
    return _get_past_dates(n)

def _initialize_driver_and_login(cred_path: str | None) -> Any | None:
    """Wrapper for workflow initialization and login."""
    return _wf_initialize_driver_and_login(cred_path, create_driver, login_bgf)


def _navigate_and_prepare_collection(driver: Any) -> bool:
    """Wrapper for workflow navigation step."""
    return _wf_navigate_and_prepare_collection(
        driver,
        run_script,
        wait_for_mix_ratio_page,
        NAVIGATION_SCRIPT,
        PAGE_LOAD_TIMEOUT,
    )


def _execute_data_collection(driver: Any) -> Any | None:
    """Wrapper for the data collection step."""
    return _wf_execute_data_collection(
        driver,
        run_script,
        wait_for_data,
        DEFAULT_SCRIPT,
        LISTENER_SCRIPT,
        DATA_COLLECTION_TIMEOUT,
    )


def _process_and_save_data(
    parsed_data: Any,
    db_path: Path | None = None,
    collected_at_override: str | None = None,
    skip_sales_check: bool = False,
) -> None:
    """Wrapper for saving collected data."""
    _wf_process_and_save_data(
        parsed_data,
        db_path,
        FIELD_ORDER,
        CODE_OUTPUT_DIR,
        ALL_SALES_DB_FILE,
        write_sales_data,
        collected_at_override=collected_at_override,
    )


def _handle_final_logs(driver: Any) -> None:
    """Wrapper for final log handling."""
    _wf_handle_final_logs(driver, CODE_OUTPUT_DIR)


def _run_collection_cycle() -> None:
    """Wrapper for the full data collection workflow."""
    cred_path = os.environ.get("CREDENTIAL_FILE")
    _wf_run_collection_cycle(
        cred_path,
        create_driver,
        login_bgf,
        run_script,
        wait_for_mix_ratio_page,
        wait_for_data,
        write_sales_data,
        is_7days_data_available,
        execute_collect_single_day_data,
        get_past_dates,
        CODE_OUTPUT_DIR,
        PAST7_DB_FILE,
        ALL_SALES_DB_FILE,
        DEFAULT_SCRIPT,
        LISTENER_SCRIPT,
        NAVIGATION_SCRIPT,
        FIELD_ORDER,
        PAGE_LOAD_TIMEOUT,
        DATA_COLLECTION_TIMEOUT,
    )


def main() -> None:
    """
    Main execution function: runs the browser, collects data, and saves it.
    """
    log.info("Starting single data collection cycle...", extra={'tag': 'main'})
    _run_collection_cycle()
    log.info("Single data collection cycle finished.", extra={'tag': 'main'})


if __name__ == "__main__":
    main()
