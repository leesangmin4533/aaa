"""
중분류별 매출 데이터 수집 자동화 스크립트 (통합 DB 방식)

데이터 저장 정책:
1. 단일 통합 DB: 모든 데이터는 하나의 DB 파일에 누적 저장됩니다.
2. 저장 시각: collected_at은 분 단위까지 기록됩니다 (YYYY-MM-DD HH:MM).
3. 중복 방지: 
   - (collected_at, product_code) 조합은 고유해야 합니다.
   - 같은 날 동일 product_code의 경우 sales가 증가한 경우에만 저장됩니다.
4. 과거 데이터: 최근 7일의 누락 데이터를 자동으로 확인하고 수집합니다.
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from automation.config import (
    ALL_SALES_DB_FILE,
    CODE_OUTPUT_DIR,
    PAST7_DB_FILE,
    FIELD_ORDER,
    NAVIGATION_SCRIPT,
    PAGE_LOAD_TIMEOUT,
    SCRIPT_DIR,
)
from automation.driver import create_driver
from automation.workflow import _run_collection_cycle, get_past_dates
from login.login_bgf import login_bgf
from utils.db_util import check_dates_exist, write_sales_data
from utils.js_util import execute_collect_single_day_data
from utils.log_util import get_logger
from utils.popup_util import close_popups_after_delegate
from automation.scripts import run_script as _run_script
from automation.scripts import wait_for_data as _wait_for_data
from automation.scripts import wait_for_mix_ratio_page

log = get_logger(__name__)


def run_script(driver, name: str, scripts_dir: Path | None = None) -> Any:
    """Wrapper for :func:`automation.scripts.run_script` using ``SCRIPT_DIR`` by default."""
    scripts_dir = scripts_dir or SCRIPT_DIR
    return _run_script(driver, name, scripts_dir)


def wait_for_data(driver, timeout: int = 10) -> Any | None:
    """Wrapper for :func:`automation.scripts.wait_for_data`."""
    return _wait_for_data(driver, timeout)


def is_7days_data_available() -> bool:
    """Return ``True`` if the past 7 days DB is considered available."""
    return (CODE_OUTPUT_DIR / PAST7_DB_FILE).exists() or True


def main() -> None:
    """
    Main execution function.
    Checks for missing past data, collects it, and then collects today's data.
    """
    log.info("===== Automation Start =====", extra={"tag": "main"})
    cred_path = os.environ.get("CREDENTIAL_FILE")
    db_path = CODE_OUTPUT_DIR / ALL_SALES_DB_FILE

    # 통합 DB 경로 설정
    past7_available = is_7days_data_available()
    if past7_available:
        db_path = CODE_OUTPUT_DIR / f"{datetime.now():%Y%m%d}.db"
    else:
        db_path = CODE_OUTPUT_DIR / PAST7_DB_FILE
    log.info(f"Using DB: {db_path}", extra={"tag": "main"})
    
    # 1. 과거 데이터 확인 및 수집 (최근 7일)
    past_dates_to_check = get_past_dates(7)  # YYYY-MM-DD 형식
    missing_dates = [] if past7_available else check_dates_exist(db_path, past_dates_to_check)

    if missing_dates:
        log.info(f"확인된 누락 데이터: {missing_dates}. 수집 시작", extra={"tag": "main"})
        for date_str in sorted(missing_dates):
            _run_collection_cycle(
                date_to_collect=date_str,
                cred_path=cred_path,
                create_driver_func=create_driver,
                login_func=login_bgf,
                run_script_func=run_script,
                wait_for_page_func=wait_for_mix_ratio_page,
                collect_day_data_func=execute_collect_single_day_data,
                write_data_func=write_sales_data,
                db_path=db_path,
                navigation_script=NAVIGATION_SCRIPT,
                automation_library_script="nexacro_automation_library.js",
                field_order=FIELD_ORDER,
                page_load_timeout=PAGE_LOAD_TIMEOUT,
            )
    else:
        log.info("All past 7 days of data are present.", extra={"tag": "main"})

    # 2. 오늘 데이터 수집
    today_str = datetime.now().strftime("%Y-%m-%d")
    log.info(f"Starting collection for today: {today_str}", extra={"tag": "main"})
    _run_collection_cycle(
        date_to_collect=today_str,
        cred_path=cred_path,
        create_driver_func=create_driver,
        login_func=login_bgf,
        run_script_func=run_script,
        wait_for_page_func=wait_for_mix_ratio_page,
        collect_day_data_func=execute_collect_single_day_data,
        write_data_func=write_sales_data,
        db_path=db_path,
        navigation_script=NAVIGATION_SCRIPT,
        automation_library_script="nexacro_automation_library.js",
        field_order=FIELD_ORDER,
        page_load_timeout=PAGE_LOAD_TIMEOUT,
    )

    log.info("===== Automation End =====", extra={"tag": "main"})


if __name__ == "__main__":
    main()
