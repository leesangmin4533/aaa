import logging
import sys
from pathlib import Path

# Add the project root to sys.path before importing project modules
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.logger_config import setup_logging

from analysis.jumeokbap_prediction import (
    get_configured_db_path,
    predict_jumeokbap_quantity,
    recommend_product_mix,
)
import sqlite3
from datetime import datetime


# Configure logging using the shared project settings
logger = setup_logging(ROOT_DIR)

JUMEOKBAP_DB_PATH = (
    ROOT_DIR / "code_outputs" / "db" / "jumeokbap_predictions.db"
)


def save_prediction_to_db(forecast: float, mix_recommendations: dict):
    conn = sqlite3.connect(JUMEOKBAP_DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS jumeokbap_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_date TEXT,
            forecast REAL,
            mix_recommendations TEXT
        )
    """
    )

    prediction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Convert dict to string for storage
    mix_recommendations_str = str(mix_recommendations)

    cursor.execute(
        "INSERT INTO jumeokbap_predictions (prediction_date, forecast,"
        " mix_recommendations) VALUES (?, ?, ?)",
        (prediction_date, forecast, mix_recommendations_str),
    )
    conn.commit()
    conn.close()
    logger.info(f"예측 결과가 {JUMEOKBAP_DB_PATH}에 저장되었습니다.")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=ROOT_DIR / "logs" / "automation.log",
)


def main():
    """ """
    try:
        logger.info("")
        db_path = get_configured_db_path()

        if not db_path:
            logger.error("")
            return

        logger.info(f"'{db_path}' ")

        tomorrow_forecast = predict_jumeokbap_quantity(db_path)
        mix_recommendations = recommend_product_mix(db_path)

        save_prediction_to_db(tomorrow_forecast, mix_recommendations)

    except FileNotFoundError:
        logger.error(f": . : {db_path}")
    except Exception as e:
        logger.error(f": {e}")


if __name__ == "__main__":
    main()
