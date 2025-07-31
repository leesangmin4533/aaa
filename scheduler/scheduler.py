import schedule
import time
import subprocess
import sys
from pathlib import Path
import json

# Add the project root to the Python path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.log_util import get_logger

log = get_logger(__name__)

def job():
    """Runs the main automation script for all configured stores."""
    log.info("Scheduler triggered. Starting automation for all stores.")
    try:
        # Execute main.py which will handle all stores sequentially
        subprocess.run([sys.executable, str(ROOT_DIR / 'main.py')], check=True)
        log.info("Scheduled job finished successfully for all stores.")
    except subprocess.CalledProcessError as e:
        log.error(f"Scheduled job failed with exit code {e.returncode}")
    except Exception as e:
        log.error(f"An unexpected error occurred during the scheduled job: {e}")

# Schedule the job to run at the start of every hour
schedule.every().hour.at(":00").do(job)

log.info("Scheduler started. Waiting for the next scheduled run...")

while True:
    schedule.run_pending()
    time.sleep(1)
