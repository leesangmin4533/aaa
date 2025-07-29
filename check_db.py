import sqlite3
from pathlib import Path

db_path = Path(
    "C:/Users/kanur/OneDrive/문서/GitHub/aaa/code_outputs/all_sales_data.db"
)

if not db_path.exists():
    print(f"Database file not found: {db_path}")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM mid_sales WHERE mid_code = '002' "
            "AND SUBSTR(collected_at, 1, 10) = '2025-07-14'"
        )
        result = cursor.fetchone()[0]
        conn.close()
        print(f"Count of mid_code '002' for 2025-07-14: {result}")
    except sqlite3.OperationalError as e:
        print(
            "Database error: %s. This might happen if the table does not "
            "exist yet.",
            e,
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
