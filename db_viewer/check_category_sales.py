import sqlite3
from pathlib import Path

# 프로젝트 루트 경로 설정
ROOT_DIR = Path(__file__).resolve().parents[1]
db_path = ROOT_DIR / "code_outputs" / "db" / "dongyang.db"

# 확인할 중분류 코드
MID_CODES_TO_CHECK = ['001', '002', '003', '004', '005']

print(f"Database: {db_path}")

if not db_path.exists():
    print(f"Error: Database not found at {db_path}")
else:
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for mid_code in MID_CODES_TO_CHECK:
            query = f"""
                SELECT 
                    product_name, 
                    SUM(sales) as total_sales
                FROM mid_sales 
                WHERE mid_code = '{mid_code}' 
                GROUP BY product_name
                ORDER BY total_sales DESC
            """
            cursor.execute(query)
            results = cursor.fetchall()

            print(f"\n--- Category: {mid_code} ---")
            if results:
                for row in results:
                    print(f"Product: {row[0]}, Total Sales: {row[1]}")
            else:
                print("No sales data for this category.")

        conn.close()
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
