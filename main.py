"""Main module for BGF Retail automation.

This script orchestrates the web automation process for BGF Retail, including:
  * Initializing and managing the Selenium WebDriver.
  * Handling user login and navigating to the sales analysis page.
  * Collecting sales data for past days and the current day.
  * Storing collected data into a SQLite database.
"""

from __future__ import annotations
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict

from login.login_bgf import login_bgf
from utils.popup_util import close_popups_after_delegate
from dotenv import load_dotenv

from utils.log_util import get_logger
from webdriver_utils import (
    create_driver,
    wait_for_dataset_to_load,
    run_script,
)
from data_collector import collect_and_save

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

SCRIPT_DIR: Path = Path(__file__).resolve().parent
CODE_OUTPUT_DIR: Path = Path(__file__).resolve().parent / "code_outputs"
NAVIGATION_SCRIPT: str = "scripts/navigation.js"

logger = get_logger("bgf_automation", level=logging.DEBUG)

# -----------------------------------------------------------------------------
# Core functionality
# -----------------------------------------------------------------------------



def run_automation_for_store(store_name: str, store_config: Dict[str, Any], global_config: Dict[str, Any]) -> None:
    logger.info(f"--- Starting automation for store: {store_name} ---")
    driver = None
    try:
        driver = create_driver()
        if not login_bgf(driver, credential_keys=store_config["credentials_env"]):
            logger.error(f"Login failed for store: {store_name}. Skipping.")
            return

        close_popups_after_delegate(driver)

        default_script = global_config["scripts"]["default"]
        run_script(driver, f"scripts/{default_script}")
        run_script(driver, "scripts/date_changer.js")
        run_script(driver, NAVIGATION_SCRIPT)

        if not wait_for_dataset_to_load(driver):
            logger.error(f"Failed to load mix ratio page for {store_name}. Skipping.")
            return

        db_path = SCRIPT_DIR / store_config["db_file"]
        collect_and_save(driver, db_path, store_name)

        from utils.db_util import run_all_category_predictions
        run_all_category_predictions(db_path)

    finally:
        if driver is not None:
            driver.quit()
            logger.info(f"WebDriver quit for store: {store_name}.")
    logger.info(f"--- Finished automation for store: {store_name} ---")

def main() -> None:
    logger = get_logger("bgf_automation", level=logging.DEBUG)
    logger.info("Starting BGF Retail Automation for all stores...")

    load_dotenv(SCRIPT_DIR / ".env", override=True)

    with open(SCRIPT_DIR / "config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    stores_to_run = config.get("stores", {})
    if not stores_to_run:
        logger.error("No stores found in config.json. Exiting.")
        return

    for store_name, store_config in stores_to_run.items():
        run_automation_for_store(store_name, store_config, config)

if __name__ == "__main__":
    main()
