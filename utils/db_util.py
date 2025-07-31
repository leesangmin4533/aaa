
"""
매출 데이터 DB 관리 및 예측 모듈

- 통합 DB에서 매출 데이터를 관리합니다.
- 과거 판매량, 날짜, 공휴일, 날씨 데이터를 기반으로 판매량을 예측합니다.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import random
import sys
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
import holidays
import requests
import logging

if __package__:
    from .log_util import get_logger
else:  # pragma: no cover - fallback when executed directly
    sys.path.append(str(Path(__file__).resolve().parent))
    from log_util import get_logger

log = get_logger(__name__)

# --- 경로 및 상수 설정 ---
if __package__:
    from .config import DB_FILE, ROOT_DIR
else:  # pragma: no cover - fallback when executed directly
    from config import DB_FILE, ROOT_DIR

SCRIPT_DIR: Path = Path(__file__).resolve().parent.parent
CODE_OUTPUT_DIR: Path = SCRIPT_DIR / "code_outputs"
JUMEOKBAP_DB_PATH = CODE_OUTPUT_DIR / "db" / "jumeokbap_predictions.db"

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

def get_configured_db_path() -> Path:
    return ROOT_DIR / DB_FILE

def _get_value(record: dict[str, any], *keys: str):
    for k in keys:
        if k in record:
            return record[k]
    return None


def write_sales_data(records: list[dict[str, any]], db_path: Path, target_date_str: str | None = None) -> int:
    """매출 데이터를 통합 DB에 저장합니다."""
    conn = init_db(db_path)

    # target_date_str이 제공되면(과거 데이터 수집 시), 해당 날짜를 사용합니다.
    # 그렇지 않으면(오늘 데이터 수집 시), 현재 날짜를 사용합니다.
    if target_date_str:
        # 입력 형식 'YYYYMMDD'를 'YYYY-MM-DD'로 변환합니다.
        current_date = f"{target_date_str[:4]}-{target_date_str[4:6]}-{target_date_str[6:]}"
        collected_at_val = f"{current_date} 00:00:00"  # 과거 데이터는 시간을 0시로 고정합니다.
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

    # 현재 날짜의 파생 특성 및 날씨 데이터 미리 가져오기
    current_date_dt = datetime.strptime(current_date, "%Y-%m-%d").date()
    
    # 요일, 월, 주차, 공휴일 여부 계산
    weekday = current_date_dt.weekday()
    month = current_date_dt.month
    week_of_year = current_date_dt.isocalendar()[1]
    is_holiday = int(current_date_dt in holidays.KR())

    # 날씨 데이터 가져오기
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

def get_sales_data_for_training(db_path: Path) -> pd.DataFrame:
    """DB에서 주먹밥 판매 데이터를 읽어와 날짜 특성을 추가합니다."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        return pd.DataFrame()

    with sqlite3.connect(db_path) as conn:
        query = "SELECT collected_at, SUM(sales) as total_sales FROM mid_sales WHERE mid_name = '주먹밥' GROUP BY SUBSTR(collected_at, 1, 10)"
        df = pd.read_sql(query, conn)

    if df.empty:
        return pd.DataFrame()

    df['date'] = pd.to_datetime(df['collected_at']).dt.date
    df['weekday'] = df['date'].apply(lambda x: x.weekday())
    df['month'] = df['date'].apply(lambda x: x.month)
    df['week_of_year'] = df['date'].apply(lambda x: x.isocalendar()[1])
    
    kr_holidays = holidays.KR()
    df['is_holiday'] = df['date'].apply(lambda x: x in kr_holidays).astype(int)
    
    return df[['date', 'total_sales', 'weekday', 'month', 'week_of_year', 'is_holiday']]

import os
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

def get_weather_data(dates: list[datetime.date]) -> pd.DataFrame:
    """기상청 API를 통해 과거 날씨 데이터를 가져옵니다."""
    api_key = os.environ.get("KMA_API_KEY")
    if not api_key:
        log.warning("기상청 API 키가 설정되지 않았습니다. 임의의 날씨 데이터로 대체합니다.")
        weather_data = []
        for date in dates:
            temp = random.uniform(5, 25)
            rainfall = random.uniform(0, 20) if random.random() > 0.7 else 0
            weather_data.append({'date': date, 'temperature': temp, 'rainfall': rainfall})
        return pd.DataFrame(weather_data)

    weather_data = []
    # 서울의 좌표 (기상청 API는 지점별로 데이터를 제공)
    nx, ny = 60, 127 

    for date in dates:
        date_str = date.strftime('%Y%m%d')
        url = f"http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst?serviceKey={api_key}&pageNo=1&numOfRows=1000&dataType=JSON&base_date={date_str}&base_time=0500&nx={nx}&ny={ny}"
        
        try:
            log.debug(f"Weather API request URL for {date}: {url}")
            response = requests.get(url)
            response.raise_for_status() # 오류 발생 시 예외 처리
            
            log.debug(f"Weather API response for {date}: {response.text}")

            data = response.json()
            
            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            if not items:
                log.warning(f"{date}의 날씨 데이터를 가져오지 못했습니다.")
                continue

            daily_temps = [float(item['fcstValue']) for item in items if item['category'] == 'TMP']
            daily_rainfall = [float(item['fcstValue']) for item in items if item['category'] == 'PCP' and item['fcstValue'] != '강수없음']

            avg_temp = sum(daily_temps) / len(daily_temps) if daily_temps else 0
            total_rainfall = sum(daily_rainfall) if daily_rainfall else 0
            
            weather_data.append({'date': date, 'temperature': avg_temp, 'rainfall': total_rainfall})

        except requests.exceptions.RequestException as e:
            log.error(f"{date} 날씨 데이터 요청 중 오류 발생: {e}")
        except (KeyError, ValueError) as e:
            log.error(f"{date} 날씨 데이터 파싱 중 오류 발생: {e}")

    return pd.DataFrame(weather_data)

def predict_jumeokbap_quantity(db_path: Path) -> float:
    """과거 데이터와 날씨 정보를 기반으로 주먹밥 판매량을 예측합니다."""
    sales_df = get_sales_data_for_training(db_path)
    if sales_df.empty or len(sales_df) < 7:
        log.warning("학습 데이터가 부족하여 기본 예측을 수행합니다.")
        return random.uniform(50.0, 200.0)

    # 날씨 데이터 추가 (현재는 임의 데이터)
    weather_df = get_weather_data(sales_df['date'].tolist())
    df = pd.merge(sales_df, weather_df, on='date')

    features = ['weekday', 'month', 'week_of_year', 'is_holiday', 'temperature', 'rainfall']
    target = 'total_sales'

    X = df[features]
    y = df[target]

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)

    # 내일 날짜로 예측
    tomorrow = datetime.now().date() + timedelta(days=1)
    tomorrow_weather = get_weather_data([tomorrow])
    tomorrow_features = {
        'weekday': tomorrow.weekday(),
        'month': tomorrow.month,
        'week_of_year': tomorrow.isocalendar()[1],
        'is_holiday': int(tomorrow in holidays.KR()),
        'temperature': tomorrow_weather['temperature'].iloc[0],
        'rainfall': tomorrow_weather['rainfall'].iloc[0]
    }
    tomorrow_df = pd.DataFrame([tomorrow_features])
    
    prediction = model.predict(tomorrow_df[features])
    log.info(f"예측된 내일 주먹밥 판매량: {prediction[0]:.2f}개")
    return prediction[0]

def recommend_product_mix(db_path: Path, predicted_sales: float) -> list[dict[str, any]]:
    """예측된 총 판매량을 기반으로 상품 조합을 추천합니다."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        return []

    with sqlite3.connect(db_path) as conn:
        # 상품 코드도 함께 조회하도록 쿼리 수정
        query = "SELECT product_code, product_name, SUM(sales) as sales FROM mid_sales WHERE mid_name = '주먹밥' GROUP BY product_code, product_name"
        df = pd.read_sql(query, conn)

    if df.empty:
        return []

    total_sales = df['sales'].sum()
    if total_sales == 0:
        return []
        
    df['ratio'] = df['sales'] / total_sales
    
    recommendations = []
    for _, row in df.iterrows():
        recommendations.append({
            "product_code": row["product_code"],
            "product_name": row["product_name"],
            "recommended_quantity": int(predicted_sales * row["ratio"])
        })
        
    log.info(f"추천 상품 조합: {recommendations}")
    return recommendations

# --- 실행 함수 ---

def run_jumeokbap_prediction_and_save():
    """주먹밥 판매량 예측을 실행하고 결과를 DB에 저장합니다."""
    try:
        db_path = get_configured_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        if not db_path.exists():
            log.info(
                f"데이터베이스가 없어 새로 생성합니다: {db_path}",
                extra={"tag": "system"},
            )
            init_db(db_path)

        forecast = predict_jumeokbap_quantity(db_path)
        mix = recommend_product_mix(db_path, forecast)

        # 예측 결과 저장
        JUMEOKBAP_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(JUMEOKBAP_DB_PATH) as conn:
            cursor = conn.cursor()
            # 1. 예측 마스터 테이블 생성
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS jumeokbap_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                prediction_date TEXT, 
                forecast REAL
            )
            """)
            # 2. 예측 아이템 상세 테이블 생성
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS jumeokbap_prediction_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER,
                product_code TEXT,
                product_name TEXT,
                recommended_quantity INTEGER,
                FOREIGN KEY (prediction_id) REFERENCES jumeokbap_predictions (id)
            )
            """)
            
            prediction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 3. 마스터 테이블에 예측 정보 삽입
            cursor.execute(
                "INSERT INTO jumeokbap_predictions (prediction_date, forecast) VALUES (?, ?)",
                (prediction_date, forecast)
            )
            prediction_id = cursor.lastrowid # 방금 삽입된 마스터 레코드의 ID 가져오기

            # 4. 아이템 테이블에 추천 상품 목록 삽입
            if mix:
                item_insert_sql = "INSERT INTO jumeokbap_prediction_items (prediction_id, product_code, product_name, recommended_quantity) VALUES (?, ?, ?, ?)"
                items_to_insert = [
                    (prediction_id, item['product_code'], item['product_name'], item['recommended_quantity'])
                    for item in mix
                ]
                cursor.executemany(item_insert_sql, items_to_insert)

            conn.commit()
        log.info(f"예측 결과가 {JUMEOKBAP_DB_PATH}에 저장되었습니다.")

    except Exception as e:
        log.error(f"주먹밥 예측 중 오류 발생: {e}", exc_info=True)
