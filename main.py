"""Main module for BGF Retail automation demo.

This script is a lightweight reconstruction of the original `main.py` from the
BGF automation project. The goal of this module is to provide a minimal
implementation that satisfies the unit tests defined in ``tests/test_main.py``.

The core responsibilities include:
  * Reading and executing JavaScript files against a Selenium WebDriver.
  * Waiting for parsed data to become available from the page.
  * Orchestrating a data‑collection cycle that can optionally collect past
    missing days before collecting the current day's data.
  * Writing the collected data to a SQLite database via a helper function.

Several functions are deliberately simple placeholders. In production, these
would import real modules and perform substantial work (e.g. logging in to a
web application, closing pop‑ups, or navigating through a Nexacro interface).
In the unit tests, these placeholders are patched to simulate their real
behaviour. Outside of the testing environment, you may replace them with
implementations appropriate for your automation stack.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

SCRIPT_DIR: Path = Path(__file__).resolve().parent
CODE_OUTPUT_DIR: Path = Path(__file__).resolve().parent / "code_outputs"
PAST7_DB_FILE: str = "past7.db"
NAVIGATION_SCRIPT: str = "navigation.js"

# -----------------------------------------------------------------------------
# Placeholder hooks
# -----------------------------------------------------------------------------

def create_driver() -> Any:
    """Create and return a Selenium WebDriver instance."""
    raise RuntimeError("create_driver has not been implemented; patch in tests")


def login_bgf(driver: Any, credential_path: Optional[str] = None) -> bool:
    return True


def close_popups_after_delegate(delegate: Optional[callable] = None) -> None:
    return None


def wait_for_mix_ratio_page(driver: Any, timeout: int = 120) -> bool:
    return True


def execute_collect_single_day_data(driver: Any, date_str: str) -> dict:
    return {"success": False, "data": []}


def write_sales_data(records: Iterable[dict], db_path: Path) -> None:
    return None


def get_past_dates() -> list[str]:
    return []


def is_7days_data_available() -> bool:
    return False


# -----------------------------------------------------------------------------
# Core functionality
# -----------------------------------------------------------------------------

def run_script(driver: Any, name: str) -> Any:
    script_path = Path(SCRIPT_DIR) / name
    if not script_path.exists():
        raise FileNotFoundError(f"JavaScript file not found: {script_path}")
    script_text = script_path.read_text(encoding="utf-8")
    return driver.execute_script(script_text)


def wait_for_data(driver: Any, timeout: float = 60.0, poll_interval: float = 0.1) -> Optional[Any]:
    start_time = time.monotonic()
    while True:
        data = driver.execute_script("return window.__parsedData__ || null")
        if data:
            return data
        if time.monotonic() - start_time >= timeout:
            return None
        time.sleep(poll_interval)


def main() -> None:
    driver = None
    try:
        driver = create_driver()
        if not login_bgf(driver, credential_path=None):
            return

        close_popups_after_delegate(lambda: None)
        run_script(driver, NAVIGATION_SCRIPT)
        wait_for_mix_ratio_page(driver)
        wait_for_data(driver)

        need_past = not is_7days_data_available()
        if need_past:
            for past in get_past_dates():
                result = execute_collect_single_day_data(driver, past)
                data = result.get("data") if isinstance(result, dict) else None
                if data:
                    write_sales_data(data, CODE_OUTPUT_DIR / PAST7_DB_FILE)
                time.sleep(0.1)

        today_str = datetime.now().strftime("%Y%m%d")
        driver.execute_script(f"window.automation.runCollectionForDate('{today_str}')")
        collected = None
        for _ in range(2):
            collected = driver.execute_script("return window.__parsedData__ || null")
            if collected:
                break

        _browser_logs = driver.get_log("browser")
        mid_logs = driver.execute_script("return window.__midCategoryLogs__ || []")
        print("중분류 클릭 로그", mid_logs)

        if collected:
            db_path = CODE_OUTPUT_DIR / (PAST7_DB_FILE if need_past else f"{today_str}.db")
            write_sales_data(collected, db_path)
        else:
            return
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()
