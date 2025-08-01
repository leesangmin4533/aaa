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

log = logging.getLogger(__name__)

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
    conn = init_db(db_path)

    if target_date_str:
        current_date = f"{target_date_str[:4]}-{target_date_str[4:6]}-{target_date_str[6:]}"
        collected_at_val = f"{current_date} 00:00:00"
    else:
        now = datetime.now()
        collected_at_val = now.strftime("%Y-%m-%d %H:%M:%S")
        current_date = now.strftime("%Y-%m-%d")

    cur = conn.cursor()

    insert_sql = """
    INSERT INTO mid_sales (
        collected_at, mid_code, mid_name, product_code, product_name,
        sales, order_cnt, purchase, disposal, stock,
        weekday, month, week_of_year, is_holiday, temperature, rainfall
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    update_sql = """
    UPDATE mid_sales SET
        collected_at = ?, mid_code = ?, mid_name = ?, product_name = ?,
        sales = ?, order_cnt = ?, purchase = ?, disposal = ?, stock = ?,
        weekday = ?, month = ?, week_of_year = ?, is_holiday = ?, temperature = ?, rainfall = ?
    WHERE product_code = ? AND SUBSTR(collected_at, 1, 10) = ?
    """

    current_date_dt = datetime.strptime(current_date, "%Y-%m-%d").date()
    weekday = current_date_dt.weekday()
    month = current_date_dt.month
    week_of_year = current_date_dt.isocalendar()[1]
    is_holiday = int(current_date_dt in holidays.KR())

    weather_df = get_weather_data([current_date_dt])
    temperature = weather_df['temperature'].iloc[0] if not weather_df.empty else 0.0
    rainfall = weather_df['rainfall'].iloc[0] if not weather_df.empty else 0.0

    for rec in records:
        product_code = _get_value(rec, "productCode", "product_code")
        sales_raw = _get_value(rec, "sales", "SALE_QTY")
        if product_code is None or sales_raw is None:
            continue
        try:
            sales = int(sales_raw)
        except (ValueError, TypeError):
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
        if row:
            if sales > (row[0] or 0):
                cur.execute(
                    update_sql,
                    (
                        collected_at_val,
                        mid_code,
                        mid_name,
                        product_name,
                        sales,
                        order_cnt,
                        purchase,
                        disposal,
                        stock,
                        weekday, month, week_of_year, is_holiday, temperature, rainfall,
                        product_code,
                        current_date,
                    ),
                )
        else:
            cur.execute(
                insert_sql,
                (
                    collected_at_val,
                    mid_code,
                    mid_name,
                    product_code,
                    product_name,
                    sales,
                    order_cnt,
                    purchase,
                    disposal,
                    stock,
                    weekday, month, week_of_year, is_holiday, temperature, rainfall,
                ),
            )

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM mid_sales")
    count = cur.fetchone()[0]
    conn.close()
    return count

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