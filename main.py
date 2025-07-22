"""
중분류별 매출 데이터 수집 자동화 스크립트 (통합 DB 방식)

데이터 저장 정책:
1. 단일 통합 DB 사용: 모든 데이터는 하나의 DB 파일에 누적 저장됩니다.
2. 중복 방지: (수집 시각, 상품 코드) 조합을 기준으로 중복 데이터는 저장되지 않습니다.
"""

from __future__ import annotations

import os
from datetime import datetime
from functools import partial

from automation.config import (
    ALL_SALES_DB_FILE,
    CODE_OUTPUT_DIR,
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
from automation.scripts import run_script, wait_for_mix_ratio_page

log = get_logger(__name__)


def main() -> None:
    """
    Main execution function.
    Checks for missing past data, collects it, and then collects today's data.
    """
    log.info("===== Automation Start =====", extra={"tag": "main"})
    cred_path = os.environ.get("CREDENTIAL_FILE")
    db_path = CODE_OUTPUT_DIR / ALL_SALES_DB_FILE

    # SCRIPT_DIR 경로를 미리 채운 run_script 함수를 생성
    run_script_with_dir = partial(run_script, scripts_dir=SCRIPT_DIR)

    # 1. 과거 데이터 확인 및 수집
    past_dates_to_check = get_past_dates(7) # YYYY-MM-DD 형식
    missing_dates = check_dates_exist(db_path, past_dates_to_check)

    if missing_dates:
        log.info(f"Missing data for past dates: {missing_dates}. Starting collection.", extra={"tag": "main"})
        for date_str in sorted(missing_dates):
            _run_collection_cycle(
                date_to_collect=date_str,
                cred_path=cred_path,
                create_driver_func=create_driver,
                login_func=login_bgf,
                run_script_func=run_script_with_dir,
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
        run_script_func=run_script_with_dir,
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