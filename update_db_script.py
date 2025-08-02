from pathlib import Path
from utils.db_util import update_past_holiday_data

DB_PATH = Path("C:/Users/kanur/OneDrive/문서/GitHub/aaa/code_outputs/db/dongyang.db")

if __name__ == "__main__":
    update_past_holiday_data(DB_PATH)
    print("Database update script finished.")