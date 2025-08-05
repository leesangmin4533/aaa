from pathlib import Path
import sqlite3
import logging

from utils.db_util import update_past_holiday_data


DB_DIR = Path(__file__).resolve().parent / "code_outputs/db"
log = logging.getLogger(__name__)


def main() -> None:
    for db_path in DB_DIR.glob("*.db"):
        try:
            with sqlite3.connect(db_path) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA table_info(mid_sales)")
                columns = [row[1] for row in cur.fetchall()]
                if "soldout" not in columns:
                    cur.execute(
                        "ALTER TABLE mid_sales ADD COLUMN soldout INTEGER DEFAULT 0"
                    )
                    conn.commit()
                    print(f"[SUCCESS] {db_path.name}")
                else:
                    print(f"[SKIP] {db_path.name}")

            update_past_holiday_data(db_path)
        except Exception:
            log.exception(f"Error processing {db_path}")
            print(f"[ERROR] {db_path.name}")
            continue

    print("All database update tasks completed.")


if __name__ == "__main__":
    main()

