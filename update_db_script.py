from pathlib import Path
import sqlite3
import logging

from utils.db_util import update_past_holiday_data


DB_DIR = Path(__file__).resolve().parent / "code_outputs/db"
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)


def main() -> None:
    log.info("Starting database schema update process.")
    db_files = list(DB_DIR.glob("*.db"))
    if not db_files:
        log.warning(f"No database files found in {DB_DIR}")
        return

    log.info(f"Found database files: {[db.name for db in db_files]}")

    for db_path in db_files:
        log.info(f"Processing {db_path.name}...")
        try:
            with sqlite3.connect(db_path) as conn:
                cur = conn.cursor()
                # Check if mid_sales table exists
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mid_sales'")
                if cur.fetchone() is None:
                    log.info(f"Table 'mid_sales' not found in {db_path.name}. Skipping.")
                    print(f"[SKIP] {db_path.name} (no mid_sales table)")
                    continue

                cur.execute("PRAGMA table_info(mid_sales)")
                columns = [row[1] for row in cur.fetchall()]
                
                if "soldout" not in columns:
                    log.info(f"'soldout' column not found in {db_path.name}. Adding column...")
                    cur.execute(
                        "ALTER TABLE mid_sales ADD COLUMN soldout INTEGER DEFAULT 0"
                    )
                    conn.commit()
                    log.info(f"Successfully added 'soldout' column to {db_path.name}.")
                    print(f"[SUCCESS] {db_path.name}")
                else:
                    log.info(f"'soldout' column already exists in {db_path.name}. Skipping alteration.")
                    print(f"[SKIP] {db_path.name}")

            log.info(f"Updating past holiday data for {db_path.name}...")
            update_past_holiday_data(db_path)
            log.info(f"Finished updating holiday data for {db_path.name}.")

        except Exception:
            log.exception(f"An error occurred while processing {db_path.name}")
            print(f"[ERROR] {db_path.name}")
            continue

    log.info("All database update tasks completed.")


if __name__ == "__main__":
    main()
