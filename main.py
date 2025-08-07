"""(Refactored & Debug) Main module for BGF Retail automation.
"""

import json
import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import pandas as pd

from dotenv import load_dotenv

from utils.log_util import get_logger
from utils.gcs_util import download_from_gcs, upload_to_gcs
from utils.api_collector import get_session, fetch_sales_data
from prediction.xgboost import run_all_category_predictions

# --- Constants ---
SCRIPT_DIR: Path = Path(__file__).resolve().parent
CODE_OUTPUT_DIR: Path = Path(__file__).resolve().parent / "code_outputs"
GCS_BUCKET_NAME = "windy-smoke-467203-k9-automation-db"


def save_data_to_db(df: pd.DataFrame, db_path: Path, date_str: str):
    """Saves the DataFrame to the SQLite database."""
    logger = get_logger("bgf_automation")
    try:
        with sqlite3.connect(db_path) as conn:
            df['collected_at'] = pd.to_datetime(date_str).strftime('%Y-%m-%d %H:%M:%S')
            required_cols = ['mid_code', 'mid_name', 'product_code', 'product_name', 'sales', 'order_cnt', 'purchase', 'disposal', 'stock']
            for col in required_cols:
                if col not in df.columns:
                    df[col] = 0
            df.to_sql('mid_sales', conn, if_exists='append', index=False)
            logger.debug(f"Data for {date_str} saved to {db_path}")
    except Exception as e:
        logger.error(f"DB 저장 중 오류 발생: {e}", exc_info=True)

def run_automation_for_store(store_name: str, store_config: dict):
    logger = get_logger("bgf_automation", level=logging.DEBUG, store_id=store_name)
    logger.info(f"--- DEBUG: Starting automation for store: {store_name} ---")

    db_path = CODE_OUTPUT_DIR / "db" / store_config["db_file"]
    gcs_db_path = f"db/{db_path.name}"
    logger.debug(f"DB path: {db_path}, GCS path: {gcs_db_path}")

    try:
        logger.debug("Downloading DB from GCS...")
        download_from_gcs(GCS_BUCKET_NAME, gcs_db_path, db_path)
        logger.debug("DB download complete.")

        credentials = {
            "id": os.environ.get(store_config["credentials_env"]["id"]),
            "password": os.environ.get(store_config["credentials_env"]["password"])
        }
        logger.debug("Credentials prepared. Getting session...")
        session = get_session(credentials)
        if not session:
            logger.error("Failed to get session. Aborting for this store.")
            return
        logger.debug("Session created successfully.")

        today = datetime.now().date()
        logger.debug(f"Data collection loop started for 8 days until {today}.")
        for i in range(7, -1, -1):
            target_date = today - timedelta(days=i)
            date_str = target_date.strftime("%Y%m%d")
            logger.debug(f"Fetching data for date: {date_str}")
            sales_df = fetch_sales_data(session, store_config["store_code"], date_str)
            if sales_df is not None and not sales_df.empty:
                logger.debug(f"Data received for {date_str}. Saving to DB...")
                save_data_to_db(sales_df, db_path, date_str)
                logger.debug(f"DB save complete for {date_str}.")
            else:
                logger.debug(f"No data for {date_str}. Skipping DB save.")
        
        logger.debug("Data collection loop finished. Starting prediction step...")
        run_all_category_predictions(db_path)
        logger.debug("Prediction step finished.")

    except Exception as e:
        logger.error(f"CRITICAL ERROR in run_automation_for_store for {store_name}: {e}", exc_info=True)
    finally:
        if db_path.exists():
            logger.debug(f"Uploading DB to GCS...")
            upload_to_gcs(GCS_BUCKET_NAME, db_path, gcs_db_path)
            logger.debug("DB upload complete.")

    logger.info(f"--- DEBUG: Finished automation for store: {store_name} ---")

def main():
    logger = get_logger("bgf_automation", level=logging.DEBUG)
    logger.info("--- DEBUG: Main function started ---")
    load_dotenv(SCRIPT_DIR / ".env", override=True)

    try:
        with open(SCRIPT_DIR / "config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        logger.debug("Config.json loaded.")
    except Exception as e:
        logger.error(f"Failed to load config.json: {e}", exc_info=True)
        return

    for store_name, store_config in config.get("stores", {}).items():
        logger.debug(f"Processing store: {store_name}")
        run_automation_for_store(store_name, store_config)
    
    logger.info("--- DEBUG: Main function finished ---")

if __name__ == "__main__":
    main()