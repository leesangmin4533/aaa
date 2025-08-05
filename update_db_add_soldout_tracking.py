import sqlite3
from pathlib import Path
import sys

# Add the project root to the Python path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.log_util import get_logger

log = get_logger(__name__)

def column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table."""
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def add_soldout_tracking_columns(db_path: Path):
    """Adds soldout_since and soldout_duration_hours columns to the mid_sales table."""
    log.info(f"Checking database: {db_path.name}")
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mid_sales';")
            if cursor.fetchone() is None:
                log.warning(f"Table 'mid_sales' not found in {db_path.name}. Skipping.")
                return

            # Add soldout_since column if it doesn't exist
            if not column_exists(cursor, 'mid_sales', 'soldout_since'):
                log.info("Adding 'soldout_since' column...")
                cursor.execute("ALTER TABLE mid_sales ADD COLUMN soldout_since TEXT")
            else:
                log.info("'soldout_since' column already exists.")

            # Add soldout_duration_hours column if it doesn't exist
            if not column_exists(cursor, 'mid_sales', 'soldout_duration_hours'):
                log.info("Adding 'soldout_duration_hours' column...")
                cursor.execute("ALTER TABLE mid_sales ADD COLUMN soldout_duration_hours REAL DEFAULT 0")
            else:
                log.info("'soldout_duration_hours' column already exists.")
            
            conn.commit()
            log.info(f"Database schema check/update complete for {db_path.name}.")

    except sqlite3.Error as e:
        log.error(f"Database error with {db_path.name}: {e}", exc_info=True)
    except Exception as e:
        log.error(f"An unexpected error occurred with {db_path.name}: {e}", exc_info=True)

def main():
    db_directory = ROOT_DIR / 'code_outputs' / 'db'
    if not db_directory.exists():
        log.error(f"Database directory not found: {db_directory}")
        return

    log.info(f"Starting database schema migration in: {db_directory}")
    for db_file in db_directory.glob("*.db"):
        add_soldout_tracking_columns(db_file)
    log.info("All databases have been checked.")

if __name__ == "__main__":
    main()
