import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import logging
import pandas as pd
import holidays

# prediction.model 모듈을 임포트하기 위해 경로 추가
import sys
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from prediction.model import get_training_data_for_category, train_and_predict, get_weather_data, recommend_product_mix
from prediction.monitor import update_performance_log

from utils.log_util import get_logger

log = get_logger(__name__, level=logging.DEBUG)

# --- 데이터베이스 관리 함수 ---

def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS mid_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        collected_at TEXT, mid_code TEXT, mid_name TEXT, product_code TEXT, 
        product_name TEXT, sales INTEGER, order_cnt INTEGER, purchase INTEGER, 
        disposal INTEGER, stock INTEGER,
        weekday INTEGER, month INTEGER, week_of_year INTEGER, is_holiday INTEGER,
        temperature REAL, rainfall REAL,
        UNIQUE(collected_at, product_code)
    );
    """)
    conn.commit()
    return conn


def _get_value(record: dict[str, any], *keys: str):
    for k in keys:
        if k in record:
            return record[k]
    return None


def write_sales_data(records: list[dict[str, any]], db_path: Path, target_date_str: str | None = None) -> int:
    """매출 데이터를 통합 DB에 저장합니다."""
    log.info(f"DB: {db_path.name}. Received {len(records)} records to write for date: {target_date_str or 'today'}.")
    if not records:
        log.warning("Received an empty list of records. Nothing to write.")
        return 0
    
    processed_count = 0
    skipped_count = 0
    conn = None  # Initialize conn to None

    try:
        conn = init_db(db_path)
        log.debug(f"DB connection to {db_path.name} successful.")
        cur = conn.cursor()

        if target_date_str:
            current_date = f"{target_date_str[:4]}-{target_date_str[4:6]}-{target_date_str[6:]}"
            collected_at_val = f"{current_date} 00:00:00"
        else:
            now = datetime.now()
            collected_at_val = now.strftime("%Y-%m-%d %H:%M:%S")
            current_date = now.strftime("%Y-%m-%d")

        current_date_dt = datetime.strptime(current_date, "%Y-%m-%d").date()
        weekday = current_date_dt.weekday()
        month = current_date_dt.month
        week_of_year = current_date_dt.isocalendar()[1]
        # Determine is_holiday based on new rules
        is_holiday_val = 0 # Default to weekday
        if current_date_dt in holidays.KR():
            is_holiday_val = 1 # Public holiday
        elif current_date_dt.weekday() == 5: # Saturday (Monday is 0, Sunday is 6)
            is_holiday_val = 2 # Saturday
        
        is_holiday = is_holiday_val

        weather_df = get_weather_data([current_date_dt])
        temperature = weather_df['temperature'].iloc[0] if not weather_df.empty else 0.0
        rainfall = weather_df['rainfall'].iloc[0] if not weather_df.empty else 0.0

        for i, rec in enumerate(records):
            log.debug(f"Processing record {i+1}/{len(records)}: {rec}")
            try:
                product_code = _get_value(rec, "productCode", "product_code")
                sales_raw = _get_value(rec, "sales", "SALE_QTY")
                
                if product_code is None or sales_raw is None:
                    log.warning(f"Record {i+1} is missing product_code or sales. Skipping. Record: {rec}")
                    skipped_count += 1
                    continue
                
                try:
                    sales = int(sales_raw)
                except (ValueError, TypeError):
                    log.warning(f"Record {i+1} has invalid sales value '{sales_raw}'. Skipping. Record: {rec}")
                    skipped_count += 1
                    continue

                mid_code = _get_value(rec, "midCode", "mid_code")
                mid_name = _get_value(rec, "midName", "mid_name")
                product_name = _get_value(rec, "productName", "product_name")
                order_cnt = _get_value(rec, "order", "order_cnt", "ORD_QTY")
                purchase = _get_value(rec, "purchase", "BUY_QTY")
                disposal = _get_value(rec, "disposal", "DISUSE_QTY")
                stock = _get_value(rec, "stock", "STOCK_QTY")

                cur.execute(
                    "SELECT sales FROM mid_sales WHERE product_code=? AND SUBSTR(collected_at,1,10)=?",
                    (product_code, current_date),
                )
                row = cur.fetchone()
                
                log.debug(f"Product: {product_code}, Date: {current_date}, New Sales: {sales}, Existing Row: {row}")

                cur.execute(
                    """INSERT OR REPLACE INTO mid_sales (collected_at, mid_code, mid_name, product_code, product_name, sales, order_cnt, purchase, disposal, stock, weekday, month, week_of_year, is_holiday, temperature, rainfall) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (collected_at_val, mid_code, mid_name, product_code, product_name, sales, order_cnt, purchase, disposal, stock, weekday, month, week_of_year, is_holiday, temperature, rainfall)
                )
                processed_count += 1
                log.debug(f"Inserted or updated record for {product_code} with sales {sales}.")
            except Exception as e:
                log.error(f"Error processing record {i+1}: {rec}. Error: {e}", exc_info=True)
                skipped_count += 1

        conn.commit()
        log.info(f"DB: {db_path.name}. Wrote/Updated {processed_count} records. Skipped {skipped_count}.")

        # Final weather data update
        cur.execute(
            """UPDATE mid_sales SET weekday = ?, month = ?, week_of_year = ?, is_holiday = ?, temperature = ?, rainfall = ? WHERE SUBSTR(collected_at, 1, 10) = ?""",
            (weekday, month, week_of_year, is_holiday, temperature, rainfall, current_date)
        )
        conn.commit()
        log.debug(f"Final weather update for {current_date} completed.")

        cur.execute("SELECT COUNT(*) FROM mid_sales")
        count = cur.fetchone()[0]
        log.info(f"Total rows in {db_path.name}: {count}.")
        return count

    except sqlite3.Error as e:
        log.error(f"Database error in write_sales_data for {db_path.name}: {e}", exc_info=True)
        return 0 # Return 0 as no records were successfully written
    except Exception as e:
        log.error(f"An unexpected error occurred in write_sales_data for {db_path.name}: {e}", exc_info=True)
        return 0
    finally:
        if conn:
            conn.close()
            log.debug(f"DB connection to {db_path.name} closed.")

def update_past_holiday_data(db_path: Path):
    """
    mid_sales 테이블의 과거 데이터에 대해 is_holiday 값을 새로운 규칙에 맞춰 업데이트합니다.
    0: 평일, 1: 공휴일, 2: 토요일
    """
    log.info(f"Updating past holiday data for {db_path.name}...")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # 모든 고유한 날짜를 가져옵니다.
        cur.execute("SELECT DISTINCT SUBSTR(collected_at, 1, 10) FROM mid_sales")
        dates_in_db = [row[0] for row in cur.fetchall()]

        updated_count = 0
        for date_str in dates_in_db:
            current_date_dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            is_holiday_val = 0 # Default to weekday
            if current_date_dt in holidays.KR():
                is_holiday_val = 1 # Public holiday
            elif current_date_dt.weekday() == 5: # Saturday (Monday is 0, Sunday is 6)
                is_holiday_val = 2 # Saturday
            
            cur.execute(
                """UPDATE mid_sales SET is_holiday = ? WHERE SUBSTR(collected_at, 1, 10) = ?""",
                (is_holiday_val, date_str)
            )
            updated_count += cur.rowcount
        
        conn.commit()
        log.info(f"Successfully updated {updated_count} records in {db_path.name} for is_holiday.")

    except sqlite3.Error as e:
        log.error(f"Database error in update_past_holiday_data for {db_path.name}: {e}", exc_info=True)
    except Exception as e:
        log.error(f"An unexpected error occurred in update_past_holiday_data for {db_path.name}: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            log.debug(f"DB connection to {db_path.name} closed.")

def check_dates_exist(db_path: Path, dates_to_check: list[str]) -> list[str]:
    """주어진 날짜 목록 중 DB에 데이터가 없는 날짜를 찾아 반환합니다."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        return dates_to_check

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    missing_dates = []
    for date_str in dates_to_check:
        cur.execute("SELECT 1 FROM mid_sales WHERE SUBSTR(collected_at, 1, 10) = ? LIMIT 1", (date_str,))
        if cur.fetchone() is None:
            missing_dates.append(date_str)
            
    conn.close()
    log.info(f"DB에 없는 날짜: {missing_dates}", extra={'tag': 'db'})
    return missing_dates

# --- 예측 모델 구현 ---

def init_prediction_db(db_path: Path):
    """모든 카테고리의 예측 결과를 저장할 DB와 테이블을 초기화합니다."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS category_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_date TEXT, -- 예측을 수행한 날짜
            target_date TEXT,     -- 예측 대상 날짜
            mid_code TEXT,        -- 중분류 코드
            mid_name TEXT,        -- 중분류명
            predicted_sales REAL, -- 예측된 판매량
            UNIQUE(target_date, mid_code)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS category_prediction_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER, -- category_predictions 테이블의 id 참조
            product_code TEXT,
            product_name TEXT,
            recommended_quantity INTEGER,
            FOREIGN KEY (prediction_id) REFERENCES category_predictions (id)
        )
        """)
        conn.commit()

def run_all_category_predictions(sales_db_path: Path):
    """모든 중분류에 대해 판매량 예측을 실행하고 결과를 DB에 저장합니다."""
    store_name = sales_db_path.stem
    prediction_db_path = sales_db_path.parent / f"category_predictions_{store_name}.db"
    init_prediction_db(prediction_db_path)

    log.info(f"[{store_name}] 모든 카테고리 예측 시작...")

    with sqlite3.connect(sales_db_path) as conn:
        mid_categories = pd.read_sql("SELECT DISTINCT mid_code, mid_name FROM mid_sales", conn)
    
    predictions_to_save = []
    prediction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    with sqlite3.connect(prediction_db_path) as conn:
        cursor = conn.cursor()
        for index, row in mid_categories.iterrows():
            mid_code = row['mid_code']
            mid_name = row['mid_name']
            
            training_data = get_training_data_for_category(sales_db_path, mid_code)
            predicted_sales = train_and_predict(mid_code, training_data)
            
            # category_predictions 테이블에 예측 결과 저장
            cursor.execute(""" 
            INSERT OR REPLACE INTO category_predictions 
            (prediction_date, target_date, mid_code, mid_name, predicted_sales)
            VALUES (?, ?, ?, ?, ?)
            """, (prediction_date, target_date, mid_code, mid_name, predicted_sales))
            prediction_id = cursor.lastrowid # 방금 삽입된 예측의 ID

            # 상품 조합 추천 및 저장
            recommended_mix = recommend_product_mix(sales_db_path, mid_code, predicted_sales)
            if recommended_mix:
                item_insert_sql = """
                INSERT INTO category_prediction_items 
                (prediction_id, product_code, product_name, recommended_quantity)
                VALUES (?, ?, ?, ?)
                """
                items_to_insert = [
                    (prediction_id, item['product_code'], item['product_name'], item['recommended_quantity'])
                    for item in recommended_mix
                ]
                cursor.executemany(item_insert_sql, items_to_insert)
        conn.commit()
    
    log.info(f"[{store_name}] 총 {len(mid_categories)}개 카테고리 예측 및 상품 조합 저장 완료. DB 저장 위치: {prediction_db_path}")

    # 모델 성능 모니터링 실행
    update_performance_log(sales_db_path, prediction_db_path)