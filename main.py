"""
중분류별 매출 데이터 수집 자동화 스크립트

데이터 저장 정책:
1. 단일 통합 DB: 모든 데이터는 하나의 DB 파일에 누적 저장됩니다.
2. 저장 시각: collected_at은 분 단위(YYYY-MM-DD HH:MM)까지 기록합니다.
3. 중복 방지: (collected_at, product_code) 조합은 고유해야 하며,
   동일 일자 동일 product_code는 sales가 증가한 경우에만 저장합니다.
4. 과거 데이터: 최근 7일의 누락 데이터를 자동으로 확인하고 수집합니다.
"""

from __future__ import annotations

import argparse

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

    PAGE_LOAD_TIMEOUT,
    SCRIPT_DIR,
    DEFAULT_SCRIPT,
    LISTENER_SCRIPT,
    NAVIGATION_SCRIPT,
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





def main() -> None:
    """
    Main execution function.
    Checks for missing past data, collects it, and then collects today's data.
    """
    try:
        log.info("===== Automation Start =====", extra={"tag": "main"})
        log.info(f"시작 시각: {datetime.now():%Y-%m-%d %H:%M:%S}", extra={"tag": "main"})
        log.info(f"Python 프로세스 ID: {os.getpid()}", extra={"tag": "main"})

        cred_path = os.environ.get("CREDENTIAL_FILE")
        db_path = CODE_OUTPUT_DIR / ALL_SALES_DB_FILE

        log.info(f"Using DB: {db_path}", extra={"tag": "main"})
        
        # 1. 오늘 데이터 수집
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
            automation_library_script=DEFAULT_SCRIPT,
            navigation_script=NAVIGATION_SCRIPT, # 추가된 매개변수
            field_order=FIELD_ORDER,
            page_load_timeout=PAGE_LOAD_TIMEOUT,
        )

        log.info("===== Automation End =====", extra={"tag": "main"})
    except Exception as e:
        log.error(f"An error occurred: {str(e)}", extra={"tag": "main"})
        raise
    finally:
        log.info("===== Automation Complete =====", extra={"tag": "main"})
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BGF Retail Automation Script")
    parser.add_argument(
        "--collect-mid-categories",
        action="store_true",
        help="Run the mid-category collection workflow."
    )
    parser.add_argument(
        "--verify-sales-quantity",
        action="store_true",
        help="Run the sales quantity verification workflow."
    )
    args = parser.parse_args()

    if args.collect_mid_categories:
        from automation.workflow import run_mid_category_collection
        from automation.scripts import collect_mid_category_data

        cred_path = os.environ.get("CREDENTIAL_FILE")
        save_path = CODE_OUTPUT_DIR / "mid_products.db"

        run_mid_category_collection(
            cred_path=cred_path,
            create_driver_func=create_driver,
            login_func=login_bgf,
            collect_mid_category_data_func=partial(collect_mid_category_data, scripts_dir=SCRIPT_DIR),
            save_path=save_path,
            scripts_dir=SCRIPT_DIR
        )
    elif args.verify_sales_quantity:
        from automation.workflow import run_sale_qty_verification

        cred_path = os.environ.get("CREDENTIAL_FILE")

        run_sale_qty_verification(
            cred_path=cred_path,
            create_driver_func=create_driver,
            login_func=login_bgf,
            run_script_func=run_script,
            wait_for_page_func=wait_for_mix_ratio_page,
            page_load_timeout=PAGE_LOAD_TIMEOUT,
            automation_library_script=DEFAULT_SCRIPT,
            navigation_script=NAVIGATION_SCRIPT,
        )
    else:
        main()
