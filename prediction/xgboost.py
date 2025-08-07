from typing import Union
import sqlite3
import pandas as pd
import xgboost
import holidays
import requests
import logging
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import random
import heapq
import pickle

from utils.log_util import get_logger
from prediction.monitor import update_performance_log

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# 중분류별 기본 유통기한(일) 매핑. 필요 시 값 추가 가능.
SHELF_LIFE_DAYS: dict[str, int] = {}

# --- 유틸리티 및 데이터 로딩 함수들 (변경 없음) ---

def get_weather_data(dates: list[datetime.date]) -> pd.DataFrame:
    """기상청 API 또는 저장된 예보 파일을 통해 날씨 데이터를 가져옵니다."""
    api_key = os.environ.get("KMA_API_KEY")
    weather_data = []
    nx, ny = 60, 127
    today = datetime.now().date()
    forecast_file = Path(__file__).resolve().parent.parent / 'code_outputs' / 'forecast.json'

    for date in dates:
        is_tomorrow = date == (today + timedelta(days=1))

        if is_tomorrow:
            if forecast_file.exists():
                try:
                    with open(forecast_file, 'r', encoding='utf-8') as f:
                        forecast_data = json.load(f)
                    if forecast_data.get('target_date') == date.strftime('%Y-%m-%d'):
                        weather_data.append({
                            'date': date, 
                            'temperature': forecast_data.get('temperature', 0.0),
                            'rainfall': forecast_data.get('rainfall', 0.0)
                        })
                        log.info(f"Loaded tomorrow's forecast from {forecast_file}")
                        continue
                    else:
                        log.warning("Forecast file is outdated. Falling back to API.")
                except (json.JSONDecodeError, IOError) as e:
                    log.error(f"Error reading forecast file: {e}. Falling back to API.")
            else:
                log.warning("Forecast file not found. Falling back to API for tomorrow's data.")

        if not api_key:
            log.warning("기상청 API 키가 없어 임의의 날씨 데이터로 대체합니다.")
            temp = random.uniform(5, 25)
            rainfall = random.uniform(0, 20) if random.random() > 0.7 else 0
            weather_data.append({'date': date, 'temperature': temp, 'rainfall': rainfall})
            continue

        if is_tomorrow:
            base_date_str = today.strftime('%Y%m%d')
            base_time_str = '0200'
            url = (
                "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getVilageFcst"
                f"?pageNo=1&numOfRows=1000&dataType=JSON&base_date={base_date_str}&base_time={base_time_str}"
                f"&nx={nx}&ny={ny}&authKey={api_key}"
            )
        elif date == today:
            request_time = datetime.now() - timedelta(hours=1)
            base_date_str = request_time.strftime('%Y%m%d')
            base_time_str = request_time.strftime('%H00')
            url = (
                "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getUltraSrtNcst"
                f"?pageNo=1&numOfRows=1000&dataType=JSON&base_date={base_date_str}&base_time={base_time_str}"
                f"&nx={nx}&ny={ny}&authKey={api_key}"
            )
        else:
             log.warning(f"{date} 는 API 조회 지원 날짜(오늘, 내일)가 아니므로 기본값으로 처리됩니다.")
             weather_data.append({'date': date, 'temperature': 0.0, 'rainfall': 0.0})
             continue

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            result_code = data.get('response', {}).get('header', {}).get('resultCode')
            if result_code != '00':
                log.warning(f"{date} 날씨 API resultCode {result_code}. 기본값으로 저장합니다.")
                weather_data.append({'date': date, 'temperature': 0.0, 'rainfall': 0.0})
                continue

            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            
            if is_tomorrow:
                temps = [float(item['fcstValue']) for item in items if item['category'] == 'TMP' and item['fcstDate'] == date.strftime('%Y%m%d')]
                rains = []
                for item in items:
                    if item['category'] == 'PCP' and item['fcstDate'] == date.strftime('%Y%m%d'):
                        value = item['fcstValue']
                        if '강수없음' in str(value):
                            rains.append(0.0)
                        else:
                            try:
                                numeric_value = float(str(value).lower().replace('mm', '').replace('cm', ''))
                                rains.append(numeric_value)
                            except (ValueError, TypeError):
                                rains.append(0.0)
                avg_temp = sum(temps) / len(temps) if temps else 0.0
                total_rainfall = sum(rains) if rains else 0.0
            else:
                avg_temp = float(next((item['obsrValue'] for item in items if item['category'] == 'T1H'), 0.0))
                total_rainfall = float(next((item['obsrValue'] for item in items if item['category'] == 'RN1'), 0.0))

            weather_data.append({'date': date, 'temperature': avg_temp, 'rainfall': total_rainfall})

        except requests.exceptions.RequestException as e:
            log.error(f"{date} 날씨 데이터 요청 중 오류: {e}. 기본값으로 대체합니다.", exc_info=True)
            weather_data.append({'date': date, 'temperature': 0.0, 'rainfall': 0.0})
        except Exception as e:
            log.error(f"{date} 날씨 데이터 파싱 중 예상치 못한 오류: {e}. 기본값으로 대체합니다.", exc_info=True)
            weather_data.append({'date': date, 'temperature': 0.0, 'rainfall': 0.0})

    return pd.DataFrame(weather_data)

def get_training_data_for_category(db_path: Path, mid_code: str) -> pd.DataFrame:
    """특정 중분류의 판매 데이터를 DB에서 읽어와 날짜 특성을 추가합니다."""
    if not db_path.exists():
        return pd.DataFrame()

    with sqlite3.connect(db_path) as conn:
        query = (
            "SELECT collected_at, "
            "SUM(sales) as total_sales, "
            "SUM(purchase) as total_purchase, "
            "SUM(disposal) as total_disposal, "
            "SUM(soldout) as total_soldout, "
            "SUM(stock) as total_stock "
            "FROM mid_sales WHERE mid_code = ? GROUP BY SUBSTR(collected_at, 1, 10)"
        )
        df = pd.read_sql(query, conn, params=(mid_code,))

    if df.empty:
        return pd.DataFrame()

    df['date'] = pd.to_datetime(df['collected_at']).dt.date
    df['weekday'] = df['date'].apply(lambda x: x.weekday())
    df['month'] = df['date'].apply(lambda x: x.month)
    df['week_of_year'] = df['date'].apply(lambda x: x.isocalendar()[1])
    kr_holidays = holidays.KR()
    df['is_holiday'] = df['date'].apply(lambda x: x in kr_holidays).astype(int)
    df['is_stockout'] = (df['total_stock'] == 0).astype(int)
    df['true_demand'] = df['total_sales'] + df['total_disposal']
    df['disposal_ratio'] = df['total_disposal'] / (df['true_demand'] + 1e-6)
    df['demand_gap'] = df['total_purchase'] - df['total_sales']
    df['shelf_life_days'] = SHELF_LIFE_DAYS.get(mid_code, 0)

    return df

# --- 신규/수정된 핵심 함수들 ---

def train_model_for_category(mid_code: str, training_df: pd.DataFrame, model_dir: Path):
    """주어진 데이터를 사용하여 특정 카테고리의 모델을 학습하고 저장합니다."""
    logger = get_logger(__name__)
    logger.info(f"[{mid_code}] 모델 학습 시작...")

    features = [
        'weekday', 'month', 'week_of_year', 'is_holiday', 'temperature',
        'rainfall', 'total_stock', 'total_soldout', 'total_purchase',
        'total_disposal', 'disposal_ratio', 'demand_gap', 'shelf_life_days',
    ]
    
    # 품절된 날의 데이터는 학습에서 제외하여 수요 왜곡 방지
    training_df = training_df[training_df['is_stockout'] == 0]

    if len(training_df) < 7:
        logger.warning(f"[{mid_code}] 학습 데이터가 7일 미만({len(training_df)}일)이므로 모델을 학습하지 않습니다.")
        return

    # 학습 데이터 기간에 대한 날씨 정보 가져오기
    weather_df = get_weather_data(training_df['date'].tolist())
    if weather_df.empty:
        logger.error(f"[{mid_code}] 학습 기간의 날씨 데이터를 가져올 수 없어 모델 학습을 중단합니다.")
        return
        
    df = pd.merge(training_df, weather_df, on='date')

    target = 'true_demand'
    X = df[features].astype('float32')
    y = df[target].astype('float32')

    model = xgboost.XGBRegressor(
        n_estimators=100,
        random_state=42,
        objective="reg:squarederror",
    )
    model.fit(X, y)

    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / f"model_{mid_code}.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"[{mid_code}] 새로운 모델을 {model_path}에 저장했습니다.")

def predict_sales_for_tomorrow(mid_code: str, latest_data_df: pd.DataFrame, model_dir: Path) -> float:
    """미리 학습된 모델을 로드하여 내일의 판매량을 예측합니다."""
    logger = get_logger(__name__)
    
    features = [
        'weekday', 'month', 'week_of_year', 'is_holiday', 'temperature',
        'rainfall', 'total_stock', 'total_soldout', 'total_purchase',
        'total_disposal', 'disposal_ratio', 'demand_gap', 'shelf_life_days',
    ]

    try:
        model_path = model_dir / f"model_{mid_code}.pkl"
        with open(model_path, "rb") as f:
            model = pickle.load(f)
        logger.info(f"[{mid_code}] 저장된 모델 {model_path}을(를) 불러왔습니다.")
    except FileNotFoundError:
        logger.warning(f"[{mid_code}] 학습된 모델 파일이 없습니다. 기본 예측(0)을 수행합니다.")
        return 0.0

    # 예측에 필요한 최신 재고량 등의 정보 가져오기
    current_stock = float(latest_data_df['total_stock'].iloc[-1]) if not latest_data_df.empty else 0.0

    # 내일 날짜 및 날씨 정보
    tomorrow = datetime.now().date() + timedelta(days=1)
    tomorrow_weather = get_weather_data([tomorrow])
    
    if tomorrow_weather.empty:
        logger.error(f"[{mid_code}] 내일 날씨 정보를 가져올 수 없어 예측을 중단합니다.")
        return 0.0

    # 내일의 특성(feature) 데이터프레임 생성
    tomorrow_features = {
        'weekday': tomorrow.weekday(),
        'month': tomorrow.month,
        'week_of_year': tomorrow.isocalendar()[1],
        'is_holiday': int(tomorrow in holidays.KR()),
        'temperature': tomorrow_weather['temperature'].iloc[0],
        'rainfall': tomorrow_weather['rainfall'].iloc[0],
        'total_stock': current_stock,
        'total_soldout': 0, 'total_purchase': 0, 'total_disposal': 0,
        'disposal_ratio': 0, 'demand_gap': 0,
        'shelf_life_days': SHELF_LIFE_DAYS.get(mid_code, 0),
    }
    tomorrow_df = pd.DataFrame([tomorrow_features])

    # 예측 수행
    prediction = model.predict(tomorrow_df[features])
    predicted_sales = max(0, float(prediction[0]))
    logger.info(f"[{mid_code}] 예측된 내일 판매량: {predicted_sales:.2f}개")
    
    return predicted_sales

# --- 상품 조합 추천 로직 (변경 없음) ---
def recommend_product_mix(db_path: Path, mid_code: str, predicted_sales: float) -> list[dict[str, any]]:
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        query = "SELECT product_code, product_name, SUM(sales) as total_sales FROM mid_sales WHERE mid_code = ? GROUP BY product_code, product_name HAVING SUM(sales) > 0"
        sales_by_product = pd.read_sql(query, conn, params=(mid_code,))
        lookback_days = 7
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        stockout_query = "SELECT product_code, SUM(CASE WHEN stock = 0 THEN 1 ELSE 0 END) AS stockout_count, COUNT(*) AS total_days FROM mid_sales WHERE mid_code = ? AND DATE(collected_at) >= ? GROUP BY product_code"
        stockout_df = pd.read_sql(stockout_query, conn, params=(mid_code, start_date))
    if sales_by_product.empty:
        return []
    sales_by_product = sales_by_product.merge(stockout_df, on="product_code", how="left")
    sales_by_product[["stockout_count", "total_days"]] = sales_by_product[["stockout_count", "total_days"]].fillna(0)
    sales_by_product["stockout_rate"] = sales_by_product.apply(lambda r: r["stockout_count"] / r["total_days"] if r["total_days"] > 0 else 0, axis=1)
    if sales_by_product.empty:
        return []
    sales_by_product = sales_by_product.sort_values(by="total_sales", ascending=False).reset_index(drop=True)
    total_sales_sum = sales_by_product["total_sales"].sum()
    if total_sales_sum == 0:
        sales_by_product["ratio"] = 1 / len(sales_by_product)
    else:
        sales_by_product["ratio"] = sales_by_product["total_sales"] / total_sales_sum
    sales_by_product["ratio"] = sales_by_product["ratio"] * (1 + sales_by_product["stockout_rate"])
    sales_by_product["ratio"] = sales_by_product["ratio"] / sales_by_product["ratio"].sum()
    product_ratio_map = dict(zip(sales_by_product["product_code"], sales_by_product["ratio"]))
    predicted_base_qty = int(predicted_sales)
    
    # 내부 헬퍼 함수들
    def _allocate_by_ratio(sales, ratio_map, base_qty):
        allocated = {}
        for _, row in sales.iterrows():
            code, name, ratio_val = row['product_code'], row['product_name'], ratio_map.get(row['product_code'], 0)
            qty = round(base_qty * ratio_val)
            if qty > 0:
                allocated[code] = {'product_name': name, 'recommended_quantity': qty, 'ratio': ratio_val}
        return allocated

    def _correct_rounding_errors(allocated, base_qty):
        diff = base_qty - sum(item['recommended_quantity'] for item in allocated.values())
        if diff > 0:
            heap = [(-data['ratio'], code) for code, data in allocated.items()]
            heapq.heapify(heap)
            for _ in range(diff):
                if not heap: break
                _, code = heapq.heappop(heap)
                allocated[code]['recommended_quantity'] += 1
        elif diff < 0:
            heap = [(data['ratio'], code) for code, data in allocated.items()]
            heapq.heapify(heap)
            for _ in range(-diff):
                if not heap: break
                _, code = heapq.heappop(heap)
                if allocated[code]['recommended_quantity'] > 1:
                    allocated[code]['recommended_quantity'] -= 1
        return allocated

    def _add_exploration_product(sales, allocated, pred_sales):
        if (pred_sales - int(pred_sales)) > 0.01:
            unpopular = sales[sales['total_sales'] < 10]
            chosen = None
            available_unpopular = unpopular[~unpopular['product_code'].isin(allocated.keys())]
            if not available_unpopular.empty:
                chosen = available_unpopular.sample(n=1).iloc[0]
            elif not unpopular.empty:
                chosen = unpopular.sample(n=1).iloc[0]
            
            if chosen is not None:
                code, name = chosen['product_code'], chosen['product_name']
                if code in allocated:
                    allocated[code]['recommended_quantity'] += 1
                else:
                    allocated[code] = {'product_name': name, 'recommended_quantity': 1, 'ratio': 0}
        return allocated

    allocated_qty = _allocate_by_ratio(sales_by_product, product_ratio_map, predicted_base_qty)
    allocated_qty = _correct_rounding_errors(allocated_qty, predicted_base_qty)
    allocated_qty = _add_exploration_product(sales_by_product, allocated_qty, predicted_sales)

    final_recommendations = []
    for prod_code, data in allocated_qty.items():
        row = sales_by_product[sales_by_product["product_code"] == prod_code].iloc[0]
        final_quantity = max(1, data["recommended_quantity"])
        reason = "stockout_adjusted" if row["stockout_rate"] > 0 else ("percentage_based" if row["total_sales"] >= 10 else "data_gathering_or_percentage_based")
        final_recommendations.append({
            "product_code": prod_code, "product_name": data["product_name"],
            "recommended_quantity": int(final_quantity), "stockout_rate": float(row["stockout_rate"]),
            "reason": reason,
        })
    return final_recommendations

# --- DB 및 메인 실행 함수 수정 ---

def init_prediction_db(db_path: Path):
    """예측 결과를 저장할 DB와 테이블을 초기화합니다."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS category_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_date TEXT, target_date TEXT, mid_code TEXT,
            mid_name TEXT, predicted_sales REAL,
            UNIQUE(target_date, mid_code)
        )"""
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS category_prediction_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER, product_code TEXT, product_name TEXT,
            recommended_quantity INTEGER,
            FOREIGN KEY (prediction_id) REFERENCES category_predictions (id)
        )"""
        )
        conn.commit()

def run_all_category_predictions(sales_db_path: Path):
    """(수정됨) 모든 중분류에 대해 '예측'만 실행하고 결과를 DB에 저장합니다."""
    store_name = sales_db_path.stem
    prediction_db_path = sales_db_path.parent / f"category_predictions_{store_name}.db"
    init_prediction_db(prediction_db_path)

    model_dir = Path(__file__).resolve().parent / "tuned_models"
    logger = get_logger(__name__, level=logging.DEBUG, store_id=store_name)
    logger.info(f"[{store_name}] 모든 카테고리 '예측' 시작...")

    with sqlite3.connect(sales_db_path) as conn:
        mid_categories = pd.read_sql("SELECT DISTINCT mid_code, mid_name FROM mid_sales", conn)

    prediction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    with sqlite3.connect(prediction_db_path) as conn:
        cursor = conn.cursor()
        for index, row in mid_categories.iterrows():
            mid_code = row['mid_code']
            mid_name = row['mid_name']

            # 예측에는 전체 데이터가 아닌, 최신 재고량 파악을 위한 데이터만 필요합니다.
            # 여기서는 간단하게 get_training_data_for_category를 재사용합니다.
            latest_data = get_training_data_for_category(sales_db_path, mid_code)
            
            # '예측' 함수 호출
            predicted_sales = predict_sales_for_tomorrow(
                mid_code, latest_data, model_dir=model_dir
            )

            cursor.execute(
                "INSERT OR REPLACE INTO category_predictions (prediction_date, target_date, mid_code, mid_name, predicted_sales) VALUES (?, ?, ?, ?, ?)",
                (prediction_date, target_date, mid_code, mid_name, predicted_sales),
            )
            prediction_id = cursor.lastrowid

            # 예측 판매량 기반으로 상품 조합 추천
            recommended_mix = recommend_product_mix(sales_db_path, mid_code, predicted_sales)
            if recommended_mix:
                item_insert_sql = "INSERT INTO category_prediction_items (prediction_id, product_code, product_name, recommended_quantity) VALUES (?, ?, ?, ?)"
                items_to_insert = [
                    (prediction_id, item['product_code'], item['product_name'], item['recommended_quantity'])
                    for item in recommended_mix
                ]
                cursor.executemany(item_insert_sql, items_to_insert)
        conn.commit()

    logger.info(f"[{store_name}] 총 {len(mid_categories)}개 카테고리 예측 및 상품 조합 저장 완료.")
    update_performance_log(sales_db_path, prediction_db_path)
