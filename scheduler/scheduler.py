import schedule
import time
import subprocess
import sys
from pathlib import Path

# Add the project root to the Python path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.log_util import get_logger

log = get_logger(__name__)

def run_main_job():
    """Runs the main automation script for all configured stores."""
    log.info("Scheduler triggered for main data collection. Starting automation.")
    try:
        subprocess.run([sys.executable, str(ROOT_DIR / 'main.py')], check=True)
        log.info("Main data collection job finished successfully.")
    except subprocess.CalledProcessError as e:
        log.error(f"Main data collection job failed with exit code {e.returncode}")
    except Exception as e:
        log.error(f"An unexpected error occurred during the main job: {e}")

def run_forecast_job():
    """Runs the forecast fetching script."""
    log.info("Scheduler triggered for forecast fetching.")
    try:
        subprocess.run([sys.executable, str(ROOT_DIR / 'scripts' / 'fetch_forecast.py')], check=True)
        log.info("Forecast fetching job finished successfully.")
    except subprocess.CalledProcessError as e:
        log.error(f"Forecast fetching job failed with exit code {e.returncode}")
    except Exception as e:
        log.error(f"An unexpected error occurred during the forecast job: {e}")

# Schedule the main data collection to run at the start of every hour
schedule.every().hour.at(":00").do(run_main_job)

# Schedule the forecast fetching to run once daily at 3 AM
schedule.every().day.at("03:00").do(run_forecast_job)

log.info("Scheduler started with hourly data collection and daily forecast jobs.")

while True:
    schedule.run_pending()
    time.sleep(1)
