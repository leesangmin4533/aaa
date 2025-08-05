from pathlib import Path
import sqlite3

from utils.db_util import update_past_holiday_data


DB_PATH = Path("C:/Users/kanur/OneDrive/문서/GitHub/aaa/code_outputs/db/dongyang.db")


def add_soldout_column(db_path: Path) -> None:
    """기존 mid_sales 테이블에 soldout 컬럼을 추가합니다."""
    if not db_path.exists():
        print(f"DB 파일이 존재하지 않습니다: {db_path}")
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(mid_sales)")
    columns = [row[1] for row in cur.fetchall()]
    if "soldout" not in columns:
        cur.execute("ALTER TABLE mid_sales ADD COLUMN soldout INTEGER DEFAULT 0")
        conn.commit()
        print("'soldout' 컬럼을 추가했습니다.")
    else:
        print("'soldout' 컬럼이 이미 존재합니다.")
    conn.close()


if __name__ == "__main__":
    add_soldout_column(DB_PATH)
    update_past_holiday_data(DB_PATH)
    print("Database update script finished.")