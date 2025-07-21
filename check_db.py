import sqlite3
from pathlib import Path

db_path = Path('C:/Users/kanur/OneDrive/문서/GitHub/aaa/code_outputs/all_sales_data.db')

if not db_path.exists():
    print(f"Database file not found: {db_path}")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(DISTINCT SUBSTR(collected_at, 1, 10)) FROM mid_sales')
        result = cursor.fetchone()[0]
        conn.close()
        print(f'Distinct dates in all_sales_data.db: {result}')
    except sqlite3.OperationalError as e:
        print(f"Database error: {e}. This might happen if the table does not exist yet.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
