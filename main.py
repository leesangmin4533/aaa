"""(Refactored) Main module for BGF Retail automation (Prediction Pipeline).

This script uses a direct API call approach, which is faster and more stable.
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
    with sqlite3.connect(db_path) as conn:
        df['collected_at'] = pd.to_datetime(date_str).strftime('%Y-%m-%d %H:%M:%S')
        required_cols = ['mid_code', 'mid_name', 'product_code', 'product_name', 'sales', 'order_cnt', 'purchase', 'disposal', 'stock']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0
        df.to_sql('mid_sales', conn, if_exists='append', index=False)

def run_automation_for_store(store_name: str, store_config: dict):
    """Runs the full data collection and prediction pipeline for a single store."""
    logger = get_logger("bgf_automation", level=logging.INFO, store_id=store_name)
    logger.info(f"--- Starting API-based automation for store: {store_name} ---")

    db_path = CODE_OUTPUT_DIR / "db" / store_config["db_file"]
    gcs_db_path = f"db/{db_path.name}"

    try:
        logger.info(f"Downloading {gcs_db_path} from GCS...")
        download_from_gcs(GCS_BUCKET_NAME, gcs_db_path, db_path)

        credentials = {
            "id": os.environ.get(store_config["credentials_env"]["id"]),
            "password": os.environ.get(store_config["credentials_env"]["password"])
        }
        session = get_session(credentials)
        if not session:
            return

        today = datetime.now().date()
        for i in range(7, -1, -1):
            target_date = today - timedelta(days=i)
            date_str = target_date.strftime("%Y%m%d")
            logger.info(f"Fetching data for {date_str}...")
            sales_df = fetch_sales_data(session, store_config["store_code"], date_str)
            if sales_df is not None and not sales_df.empty:
                save_data_to_db(sales_df, db_path, date_str)
        
        logger.info("Running prediction step...")
        run_all_category_predictions(db_path)
        logger.info("Prediction step completed.")

    except Exception as e:
        logger.error(f"An unexpected error occurred for {store_name}: {e}", exc_info=True)
    finally:
        if db_path.exists():
            logger.info(f"Uploading {db_path} to GCS...")
            upload_to_gcs(GCS_BUCKET_NAME, db_path, gcs_db_path)

    logger.info(f"--- Finished API-based automation for store: {store_name} ---")

def main():
    """Entry point of the script."""
    logger = get_logger("bgf_automation", level=logging.INFO)
    logger.info("Starting Refactored BGF Retail Automation...")
    load_dotenv(SCRIPT_DIR / ".env", override=True)

    with open(SCRIPT_DIR / "config.json", "r", encoding="utf-8") as f:
        config = json.load(f)

    for store_name, store_config in config.get("stores", {}).items():
        run_automation_for_store(store_name, store_config)

if __name__ == "__main__":
    main()
