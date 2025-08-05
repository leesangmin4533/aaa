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

from utils.log_util import get_logger
from prediction.monitor import update_performance_log

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

def get_weather_data(dates: list[datetime.date]) -> pd.DataFrame:
    """기상청 API를 통해 최근 날씨 데이터를 가져옵니다.

    현재 시점 기준으로 ±1일 이내의 날짜만 API에 요청하며, 그 외 날짜는 기본값(0)으로 처리합니다.
    """
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
    nx, ny = 60, 127
    today = datetime.now().date()

    for date in dates:
        # API 제한에 따라 현재 기준 ±1일만 요청
        if abs((today - date).days) > 1:
            log.warning(f"{date} 는 API 제한 범위를 벗어나 기본값으로 처리됩니다.")
            weather_data.append({'date': date, 'temperature': 0.0, 'rainfall': 0.0})
            continue

        request_time = datetime.now() - timedelta(hours=2)
        if date == today:
            # API 데이터 생성을 고려해 현재 시간에서 2시간을 뺀 시간을 기준으로 조회
            base_date_str = request_time.strftime('%Y%m%d')
            base_time_str = request_time.strftime('%H00')
        else:
            # 다른 날짜는 정오(12:00)를 기준으로 조회
            base_date_str = date.strftime('%Y%m%d')
            base_time_str = '1200'

        url = (
            "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getUltraSrtNcst?pageNo=1&numOfRows=1000"
            f"&dataType=JSON&base_date={base_date_str}&base_time={base_time_str}&nx={nx}&ny={ny}&authKey={api_key}"
        )

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            log.debug(
                "Weather API raw response for %s: %s",
                date,
                json.dumps(data, ensure_ascii=False),
            )

            result_code = (
                data.get('response', {}).get('header', {}).get('resultCode')
            )
            if result_code != '00':
                log.warning(f"{date} 날씨 API resultCode {result_code}. 기본값으로 저장합니다.")
                weather_data.append({'date': date, 'temperature': 0.0, 'rainfall': 0.0})
                continue

            avg_temp = 0.0
            total_rainfall = 0.0

            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            log.debug(
                "Weather API parsed items for %s: %s",
                date,
                json.dumps(items, ensure_ascii=False),
            )

            for item in items:
                category = item.get('category')
                obsr_value = item.get('obsrValue')
                if category == 'T1H':
                    try:
                        avg_temp = float(obsr_value)
                    except (ValueError, TypeError):
                        pass
                elif category == 'RN1':
                    try:
                        total_rainfall = float(obsr_value)
                    except (ValueError, TypeError):
                        pass

            weather_data.append({'date': date, 'temperature': avg_temp, 'rainfall': total_rainfall})
        except requests.exceptions.Timeout:
            log.error(f"{date} 날씨 데이터 요청 중 타임아웃 발생. 기본값으로 대체합니다.", exc_info=True)
            weather_data.append({'date': date, 'temperature': 0.0, 'rainfall': 0.0})
        except requests.exceptions.RequestException as e:
            log.error(f"{date} 날씨 데이터 요청 중 오류: {e}. 기본값으로 대체합니다.", exc_info=True)
            weather_data.append({'date': date, 'temperature': 0.0, 'rainfall': 0.0})
        except Exception as e:
            log.error(
                f"{date} 날씨 데이터 파싱 중 예상치 못한 오류: {e}. 기본값으로 대체합니다.",
                exc_info=True,
            )
            weather_data.append({'date': date, 'temperature': 0.0, 'rainfall': 0.0})

    return pd.DataFrame(weather_data)

def get_training_data_for_category(db_path: Path, mid_code: str) -> pd.DataFrame:
    """특정 중분류의 판매 데이터를 DB에서 읽어와 날짜 특성을 추가합니다."""
    if not db_path.exists():
        return pd.DataFrame()

    with sqlite3.connect(db_path) as conn:
        query = (
            "SELECT collected_at, SUM(sales) as total_sales "
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
    
    log.debug(f"[{mid_code}] get_training_data_for_category returned {len(df)} rows.")
    return df[['date', 'total_sales', 'weekday', 'month', 'week_of_year', 'is_holiday']]

def train_and_predict(mid_code: str, training_df: pd.DataFrame) -> float:
    """주어진 학습 데이터로 모델을 훈련하고 내일의 판매량을 예측합니다."""
    if training_df.empty:
        log.warning(f"[{mid_code}] 학습 데이터가 없어 기본 예측(Random)을 수행합니다.")
        return random.uniform(10.0, 50.0) # 카테고리별 기본 예측값

    if len(training_df) < 7:
        log.warning(f"[{mid_code}] 학습 데이터가 7일 미만입니다. 예측 정확도가 낮을 수 있습니다.")

    weather_df = get_weather_data(training_df['date'].tolist())
    df = pd.merge(training_df, weather_df, on='date')

    features = ['weekday', 'month', 'week_of_year', 'is_holiday', 'temperature', 'rainfall']
    target = 'total_sales'
    X = df[features].astype('float32')
    y = df[target].astype('float32')

    model = xgboost.XGBRegressor(
        n_estimators=100,
        random_state=42,
        objective="reg:squarederror",
    )
    model.fit(X, y)

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
    log.info(f"[{mid_code}] 예측된 내일 판매량: {prediction[0]:.2f}개")
    return prediction[0]


def _allocate_by_ratio(
    sales_by_product: pd.DataFrame,
    ratio_map: dict[str, float],
    predicted_base_qty: int,
) -> dict[str, dict[str, any]]:
    """비율에 따라 기본 추천 수량을 계산합니다."""
    allocated_qty: dict[str, dict[str, any]] = {}
    for _, row in sales_by_product.iterrows():
        product_code = row['product_code']
        product_name = row['product_name']
        ratio = ratio_map.get(product_code, 0)
        quantity = round(predicted_base_qty * ratio)
        if quantity > 0:
            allocated_qty[product_code] = {
                'product_name': product_name,
                'recommended_quantity': quantity,
                'ratio': ratio,
            }
    return allocated_qty


def _correct_rounding_errors(
    allocated_qty: dict[str, dict[str, any]],
    predicted_base_qty: int,
) -> dict[str, dict[str, any]]:
    """반올림 오차로 인한 수량 차이를 보정합니다."""
    current_distributed_sum = sum(
        item['recommended_quantity'] for item in allocated_qty.values()
    )
    difference = predicted_base_qty - current_distributed_sum
    if difference > 0:
        max_heap = [(-data['ratio'], code) for code, data in allocated_qty.items()]
        heapq.heapify(max_heap)
        for _ in range(difference):
            if not max_heap:
                break
            ratio, prod_code = heapq.heappop(max_heap)
            allocated_qty[prod_code]['recommended_quantity'] += 1
            heapq.heappush(max_heap, (ratio, prod_code))
        del max_heap
    elif difference < 0:
        min_heap = [(data['ratio'], code) for code, data in allocated_qty.items()]
        heapq.heapify(min_heap)
        for _ in range(-difference):
            while min_heap:
                ratio, prod_code = heapq.heappop(min_heap)
                if allocated_qty[prod_code]['recommended_quantity'] > 1:
                    allocated_qty[prod_code]['recommended_quantity'] -= 1
                    heapq.heappush(min_heap, (ratio, prod_code))
                    break
            else:
                break
        del min_heap
    return allocated_qty


def _add_exploration_product(
    sales_by_product: pd.DataFrame,
    ratio_map: dict[str, float],
    allocated_qty: dict[str, dict[str, any]],
    predicted_sales: float,
) -> dict[str, dict[str, any]]:
    """탐색을 위해 추가 상품을 선택합니다."""
    predicted_base_qty = int(predicted_sales)
    has_fractional_part = (predicted_sales - predicted_base_qty) > 0.01
    if not has_fractional_part:
        return allocated_qty

    unpopular_products_df = sales_by_product[sales_by_product['total_sales'] < 10]

    chosen_product = None
    if not unpopular_products_df.empty:
        available_unpopular = unpopular_products_df[
            ~unpopular_products_df['product_code'].isin(allocated_qty.keys())
        ]
        if not available_unpopular.empty:
            chosen_product = available_unpopular.sample(n=1).iloc[0]
        else:
            chosen_product = unpopular_products_df.sample(n=1).iloc[0]

    if chosen_product is None and not sales_by_product.empty:
        available_products = sales_by_product[
            ~sales_by_product['product_code'].isin(allocated_qty.keys())
        ]
        if not available_products.empty:
            chosen_product = available_products.sample(n=1).iloc[0]
        else:
            chosen_product = sales_by_product.sample(n=1).iloc[0]

    if chosen_product is not None and not chosen_product.empty:
        prod_code = chosen_product['product_code']
        prod_name = chosen_product['product_name']
        if prod_code in allocated_qty:
            allocated_qty[prod_code]['recommended_quantity'] += 1
        else:
            allocated_qty[prod_code] = {
                'product_name': prod_name,
                'recommended_quantity': 1,
                'ratio': ratio_map.get(prod_code, 0),
            }
        log.debug(
            f"Added exploration product {prod_name}"
        )
    return allocated_qty

def recommend_product_mix(db_path: Path, mid_code: str, predicted_sales: float) -> list[dict[str, any]]:
    """
    예측된 총 판매량을 기반으로 상품 판매 비율에 따라 추천 수량을 배분하고,
    소수점 이하가 있을 경우 데이터 부족 상품을 추가로 추천합니다.
    """
    if not db_path.exists():
        log.warning(f"Database not found at {db_path}. Cannot generate recommendations.")
        return []

    with sqlite3.connect(db_path) as conn:
        query = f"""
            SELECT 
                product_code, 
                product_name, 
                SUM(sales) as total_sales
            FROM mid_sales 
            WHERE mid_code = '{mid_code}' 
            GROUP BY product_code, product_name
            HAVING SUM(sales) > 0
        """
        sales_by_product = pd.read_sql(query, conn)

    if sales_by_product.empty:
        log.warning(f"[{mid_code}] No sales data found for any products. Cannot make recommendations. Returning empty list.")
        return []

    sales_by_product = sales_by_product.sort_values(by='total_sales', ascending=False).reset_index(drop=True)

    total_sales_sum = sales_by_product['total_sales'].sum()
    if total_sales_sum == 0:
        log.warning(f"[{mid_code}] Total sales sum is zero. Cannot calculate ratios. Distributing evenly.")
        sales_by_product['ratio'] = 1 / len(sales_by_product)
    else:
        sales_by_product['ratio'] = sales_by_product['total_sales'] / total_sales_sum

    product_ratio_map = dict(zip(sales_by_product['product_code'], sales_by_product['ratio']))

    predicted_base_qty = int(predicted_sales)
    allocated_qty = _allocate_by_ratio(
        sales_by_product, product_ratio_map, predicted_base_qty
    )
    allocated_qty = _correct_rounding_errors(
        allocated_qty, predicted_base_qty
    )
    allocated_qty = _add_exploration_product(
        sales_by_product, product_ratio_map, allocated_qty, predicted_sales
    )
    del product_ratio_map

    final_recommendations = []
    for prod_code, data in allocated_qty.items():
        # 최소 1개 추천 보장
        final_quantity = max(1, data['recommended_quantity'])
        final_recommendations.append({
            "product_code": prod_code,
            "product_name": data["product_name"],
            "recommended_quantity": int(final_quantity),
            "reason": "percentage_based" if sales_by_product[sales_by_product['product_code'] == prod_code]['total_sales'].iloc[0] >= 10 else "data_gathering_or_percentage_based"
        })

    # 최종 추천 수량 합계 로깅
    total_recommended_quantity = sum(rec['recommended_quantity'] for rec in final_recommendations)
    log.info(
        f"[{mid_code}] Predicted: {predicted_sales:.2f}. Recommended {len(final_recommendations)} types of items with total quantity of {total_recommended_quantity}."
    )
    log.info(
        "[%s] Recommendation details: %s",
        mid_code,
        json.dumps(final_recommendations, ensure_ascii=False),
    )

    return final_recommendations


def init_prediction_db(db_path: Path):
    """모든 카테고리의 예측 결과를 저장할 DB와 테이블을 초기화합니다."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS category_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_date TEXT, -- 예측을 수행한 날짜
            target_date TEXT,     -- 예측 대상 날짜
            mid_code TEXT,        -- 중분류 코드
            mid_name TEXT,        -- 중분류명
            predicted_sales REAL, -- 예측된 판매량
            UNIQUE(target_date, mid_code)
        )
        """
        )
        conn.execute(
            """
        CREATE TABLE IF NOT EXISTS category_prediction_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER, -- category_predictions 테이블의 id 참조
            product_code TEXT,
            product_name TEXT,
            recommended_quantity INTEGER,
            FOREIGN KEY (prediction_id) REFERENCES category_predictions (id)
        )
        """
        )
        conn.commit()


def run_all_category_predictions(sales_db_path: Path):
    """모든 중분류에 대해 판매량 예측을 실행하고 결과를 DB에 저장합니다."""
    store_name = sales_db_path.stem
    prediction_db_path = sales_db_path.parent / f"category_predictions_{store_name}.db"
    init_prediction_db(prediction_db_path)

    logger = get_logger(__name__, level=logging.DEBUG, store_id=store_name)
    logger.info(f"[{store_name}] 모든 카테고리 예측 시작...")

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

            cursor.execute(
                """
            INSERT OR REPLACE INTO category_predictions
            (prediction_date, target_date, mid_code, mid_name, predicted_sales)
            VALUES (?, ?, ?, ?, ?)
            """,
                (prediction_date, target_date, mid_code, mid_name, predicted_sales),
            )
            prediction_id = cursor.lastrowid

            recommended_mix = recommend_product_mix(sales_db_path, mid_code, predicted_sales)
            if recommended_mix:
                item_insert_sql = """
                INSERT INTO category_prediction_items
                (prediction_id, product_code, product_name, recommended_quantity)
                VALUES (?, ?, ?, ?)
                """
                items_to_insert = [
                    (
                        prediction_id,
                        item['product_code'],
                        item['product_name'],
                        item['recommended_quantity'],
                    )
                    for item in recommended_mix
                ]
                cursor.executemany(item_insert_sql, items_to_insert)
        conn.commit()

    logger.info(
        f"[{store_name}] 총 {len(mid_categories)}개 카테고리 예측 및 상품 조합 저장 완료. DB 저장 위치: {prediction_db_path}"
    )

    update_performance_log(sales_db_path, prediction_db_path)

