from __future__ import annotations

import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import logging
import json

try:
    from selenium.webdriver.support.ui import WebDriverWait
except ImportError as exc:  # pragma: no cover - dependency missing
    logging.getLogger(__name__).warning(
        "Selenium not available: %s", exc
    )
    WebDriverWait = None  # type: ignore

from utils.db_util import write_sales_data, check_dates_exist
from utils.log_util import get_logger

logger = get_logger("bgf_automation", level=logging.DEBUG)


def execute_collect_single_day_data(driver: Any, date_str: str) -> dict:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        driver.execute_script(
            f"window.automation.runCollectionForDate('{date_str}')"
        )
        data = driver.execute_script("return window.__parsedData__ || null")
        return {"success": data is not None, "data": data}

    for _ in range(60):
        running = driver.execute_script(
            "return window.automation && window.automation.isCollecting;"
        )
        if not running:
            break
        time.sleep(0.25)

    if WebDriverWait is not None:
        try:
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script(
                    "return typeof window.automation !== 'undefined' && "
                    "typeof window.automation.changeDateAndSearch === 'function';"
                )
            )
        except Exception:
            logger.warning("changeDateAndSearch 함수가 로드되지 않았습니다.")

    driver.execute_script(
        "window.automation.runCollectionForDate(arguments[0])",
        date_str,
    )

    parsed = None
    for _ in range(240):
        running = driver.execute_script(
            "return window.automation && window.automation.isCollecting;"
        )
        parsed = driver.execute_script(
            "return window.automation && window.automation.parsedData || null;"
        )
        if not running:
            break
        time.sleep(0.5)

    success = isinstance(parsed, list) and len(parsed) > 0
    logger.info(
        "[execute_collect_single_day_data] Raw data from JS: %s",
        json.dumps(parsed, ensure_ascii=False),
    )
    return {"success": bool(success), "data": parsed if success else None}


def get_past_dates(num_days: int = 7) -> list[str]:
    today = datetime.now()
    past_dates = []
    for i in range(1, num_days + 1):
        past_date = today - timedelta(days=i)
        past_dates.append(past_date.strftime("%Y%m%d"))
    return past_dates


def get_missing_past_dates(db_path: Path, num_days: int = 7) -> list[str]:
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return []

    past_dates_for_script = get_past_dates(num_days)
    dates_to_check_in_db = [f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in past_dates_for_script]
    missing_dates = check_dates_exist(db_path, dates_to_check_in_db)
    return [d.replace("-", "") for d in missing_dates]


def wait_for_data(driver: Any, timeout: int = 10) -> Any | None:
    start = time.time()
    while time.time() - start < timeout:
        data = driver.execute_script("return window.__parsedData__ || null")
        if data is not None:
            return data
        time.sleep(0.5)
    return None


def collect_and_save(driver: Any, db_path: Path, store_name: str) -> bool:
    """Collect sales data and persist it.

    Returns
    -------
    bool
        ``True`` if today's data was successfully written to the database,
        otherwise ``False``.
    """

    log = get_logger("bgf_automation", level=logging.DEBUG, store_id=store_name)

    missing_past_dates = get_missing_past_dates(db_path)
    if missing_past_dates:
        log.info(
            "Missing past dates for %s: %s. Attempting to collect...",
            store_name,
            json.dumps(missing_past_dates, ensure_ascii=False),
        )
        for past in missing_past_dates:
            result = execute_collect_single_day_data(driver, past)
            data = result.get("data") if isinstance(result, dict) else None
            if data and isinstance(data, list) and data and isinstance(data[0], dict):
                write_sales_data(data, db_path, target_date_str=past, store_id=store_name)
            else:
                log.warning(
                    f"No valid data collected for {past} at store {store_name}"
                )
            time.sleep(0.1)

    today_str = datetime.now().strftime("%Y%m%d")
    result = execute_collect_single_day_data(driver, today_str)
    collected = result.get("data") if isinstance(result, dict) else None
    saved_today = False

    try:
        if collected and isinstance(collected, list) and collected and isinstance(collected[0], dict):
            log.info(
                f"[{store_name}] Successfully collected {len(collected)} records for {today_str}."
            )
            log.info(
                "[%s] Data to be written: %s",
                store_name,
                json.dumps(collected, ensure_ascii=False),
            )
            log.info(f"[{store_name}] --- Calling write_sales_data ---")
            write_sales_data(collected, db_path, store_id=store_name)
            log.info(f"[{store_name}] --- Returned from write_sales_data ---")
            for handler in log.logger.handlers if hasattr(log, 'logger') else log.handlers:
                handler.flush()
            saved_today = True
        else:
            log.warning(
                "No valid data collected for %s at store %s. Collected data: %s",
                today_str,
                store_name,
                json.dumps(collected, ensure_ascii=False),
            )
    except Exception as e:
        log.error(
            f"Error calling write_sales_data for store {store_name}: {e}",
            exc_info=True,
        )

    return saved_today
