"""Main module for BGF Retail automation (Prediction Pipeline).

This script orchestrates the web automation process for BGF Retail, including:
  * Downloading the latest DB from GCS.
  * Initializing and managing the Selenium WebDriver.
  * Handling user login and navigating to the sales analysis page.
  * Collecting the latest sales data and appending it to the SQLite database.
  * Loading a pre-trained model to predict future sales.
  * Uploading the updated DB to GCS.
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
from utils.gcs_util import download_from_gcs, upload_to_gcs

# --- Constants ---
SCRIPT_DIR: Path = Path(__file__).resolve().parent
CODE_OUTPUT_DIR: Path = Path(__file__).resolve().parent / "code_outputs"
NAVIGATION_SCRIPT: str = "scripts/navigation.js"
GCS_BUCKET_NAME = "windy-smoke-467203-k9-automation-db"

logger = get_logger("bgf_automation", level=logging.DEBUG)

# --- Core functionality ---

def run_automation_for_store(store_name: str, store_config: Dict[str, Any], global_config: Dict[str, Any]) -> None:
    """Runs the data collection and prediction pipeline for a single store."""
    log = get_logger("bgf_automation", level=logging.DEBUG, store_id=store_name)
    log.info(f"--- Starting automation for store: {store_name} ---")
    driver = None
    db_path = CODE_OUTPUT_DIR / "db" / store_config["db_file"]
    gcs_db_path = f"db/{db_path.name}"

    try:
        # 1. GCS에서 최신 DB 다운로드
        log.info(f"Downloading {gcs_db_path} from GCS...")
        download_from_gcs(GCS_BUCKET_NAME, gcs_db_path, db_path)

        # 2. 데이터 수집
        log.info("Creating WebDriver...")
        driver = create_driver()
        log.info("WebDriver created successfully.")

        log.info("Logging in...")
        if not login_bgf(driver, credential_keys=store_config["credentials_env"]):
            log.error(f"Login failed for store: {store_name}. Skipping.")
            return
        log.info("Login successful.")

        close_popups_after_delegate(driver)
        default_script = global_config["scripts"]["default"]
        run_script(driver, f"scripts/{default_script}")
        run_script(driver, "scripts/date_changer.js")
        run_script(driver, NAVIGATION_SCRIPT)

        if not wait_for_dataset_to_load(driver):
            log.error(f"Failed to load mix ratio page for {store_name}. Skipping.")
            return
        
        log.info(f"Collecting and saving data to {db_path}...")
        saved = collect_and_save(driver, db_path, store_name)
        log.info("Data collection and saving process finished.")

        # 3. 예측 실행 (학습 제외)
        if not saved:
            log.warning("Data collection failed for %s. Skipping prediction stage.", store_name)
        else:
            # xgboost 모듈과 예측 함수를 동적으로 import
            from prediction.xgboost import run_all_category_predictions
            log.info("Running prediction step...")
            try:
                # 이 함수는 이제 내부적으로 예측만 수행합니다.
                run_all_category_predictions(db_path)
                log.info("Prediction step completed successfully.")
            except Exception as e:
                log.error("Prediction step failed for store %s: %s", store_name, e, exc_info=True)

    except Exception as e:
        log.error(f"An unexpected error occurred in run_automation_for_store for {store_name}: {e}", exc_info=True)
    finally:
        if driver is not None:
            driver.quit()
            log.info(f"WebDriver quit for store: {store_name}.")
        
        # 4. GCS에 업데이트된 DB 업로드
        if db_path.exists():
            log.info(f"Uploading {db_path} to GCS...")
            upload_to_gcs(GCS_BUCKET_NAME, db_path, gcs_db_path)

    log.info(f"--- Finished automation for store: {store_name} ---")

def main() -> None:
    """Entry point of the script."""
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