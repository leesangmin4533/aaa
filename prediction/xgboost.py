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

def get_weather_data(dates: list[datetime.date]) -> pd.DataFrame:
    """기상청 API 또는 저장된 예보 파일을 통해 날씨 데이터를 가져옵니다.

    - 내일 예보: forecast.json 파일에서 읽어옴
    - 오늘 또는 과거 날씨: 초단기실황 API 사용
    - 그 외: 기본값(0)으로 처리
    """
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

        # Fallback to API if forecast file is not available or outdated for tomorrow
        if not api_key:
            log.warning("기상청 API 키가 없어 임의의 날씨 데이터로 대체합니다.")
            temp = random.uniform(5, 25)
            rainfall = random.uniform(0, 20) if random.random() > 0.7 else 0
            weather_data.append({'date': date, 'temperature': temp, 'rainfall': rainfall})
            continue

        # API URL 결정 (오늘/과거 vs 내일)
        if is_tomorrow: # 단기예보
            base_date_str = today.strftime('%Y%m%d')
            base_time_str = '0200' # 새벽 2시 예보
            url = (
                "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getVilageFcst"
                f"?pageNo=1&numOfRows=1000&dataType=JSON&base_date={base_date_str}&base_time={base_time_str}"
                f"&nx={nx}&ny={ny}&authKey={api_key}"
            )
        elif date == today: # 초단기실황
            request_time = datetime.now() - timedelta(hours=1)
            base_date_str = request_time.strftime('%Y%m%d')
            base_time_str = request_time.strftime('%H00')
            url = (
                "https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getUltraSrtNcst"
                f"?pageNo=1&numOfRows=1000&dataType=JSON&base_date={base_date_str}&base_time={base_time_str}"
                f"&nx={nx}&ny={ny}&authKey={api_key}"
            )
        else: # 과거 데이터 (지원 안함)
             log.warning(f"{date} 는 API 조회 지원 날짜(오늘, 내일)가 아니므로 기본값으로 처리됩니다.")
             weather_data.append({'date': date, 'temperature': 0.0, 'rainfall': 0.0})
             continue

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            log.debug("Weather API raw response for %s: %s", date, json.dumps(data, ensure_ascii=False))

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
            else: # 오늘 실황
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

    # 파생 피처 계산
    df['true_demand'] = df['total_sales'] + df['total_disposal']
    df['disposal_ratio'] = df['total_disposal'] / (df['true_demand'] + 1e-6)
    df['demand_gap'] = df['total_purchase'] - df['total_sales']
    df['shelf_life_days'] = SHELF_LIFE_DAYS.get(mid_code, 0)

    log.debug(f"[{mid_code}] get_training_data_for_category returned {len(df)} rows.")
    return df[
        [
            'date',
            'total_sales',
            'total_purchase',
            'total_disposal',
            'total_soldout',
            'total_stock',
            'is_stockout',
            'weekday',
            'month',
            'week_of_year',
            'is_holiday',
            'true_demand',
            'disposal_ratio',
            'demand_gap',
            'shelf_life_days',
        ]
    ]


def load_or_default_model(mid_code: str, model_dir: Path):
    """주어진 디렉터리에서 사전 학습된 모델을 로드합니다.

    모델 파일이 존재하지 않으면 ``FileNotFoundError`` 를 발생시킵니다.
    """
    model_path = model_dir / f"model_{mid_code}.pkl"
    if not model_path.exists():
        raise FileNotFoundError(model_path)
    with open(model_path, "rb") as f:
        return pickle.load(f)


def train_and_predict(
    mid_code: str,
    training_df: pd.DataFrame,
    model_dir: Path | None = None,
) -> float:
    """모델을 로드하거나 필요 시 학습하여 내일의 판매량을 예측합니다."""
    features = [
        'weekday',
        'month',
        'week_of_year',
        'is_holiday',
        'temperature',
        'rainfall',
        'total_stock',
        'total_soldout',
        'total_purchase',
        'total_disposal',
        'disposal_ratio',
        'demand_gap',
        'shelf_life_days',
    ]

    model = None
    if model_dir is not None:
        try:
            model = load_or_default_model(mid_code, model_dir)
        except FileNotFoundError:
            log.warning(
                f"[{mid_code}] 모델 파일이 없어 기본 모델을 학습합니다."
            )

    if model is None:
        training_df = training_df[training_df['is_stockout'] == 0]

        if training_df.empty:
            log.warning(
                f"[{mid_code}] 학습 데이터가 없어 기본 예측(Random)을 수행합니다."
            )
            return random.uniform(10.0, 50.0)  # 카테고리별 기본 예측값

        if len(training_df) < 7:
            log.warning(
                f"[{mid_code}] 학습 데이터가 7일 미만입니다. 예측 정확도가 낮을 수 있습니다."
            )

        weather_df = get_weather_data(training_df['date'].tolist())
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

        if model_dir is not None:
            model_dir.mkdir(parents=True, exist_ok=True)
            model_path = model_dir / f"model_{mid_code}.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)
            log.info(f"[{mid_code}] 모델을 {model_path}에 저장했습니다.")

    current_stock = float(training_df['total_stock'].iloc[-1]) if not training_df.empty else 0.0

    tomorrow = datetime.now().date() + timedelta(days=1)
    tomorrow_weather = get_weather_data([tomorrow])
    tomorrow_features = {
        'weekday': tomorrow.weekday(),
        'month': tomorrow.month,
        'week_of_year': tomorrow.isocalendar()[1],
        'is_holiday': int(tomorrow in holidays.KR()),
        'temperature': tomorrow_weather['temperature'].iloc[0],
        'rainfall': tomorrow_weather['rainfall'].iloc[0],
        'total_stock': current_stock,
        'total_soldout': 0,
        'total_purchase': 0,
        'total_disposal': 0,
        'disposal_ratio': 0,
        'demand_gap': 0,
        'shelf_life_days': SHELF_LIFE_DAYS.get(mid_code, 0),
    }
    tomorrow_df = pd.DataFrame([tomorrow_features])

    prediction = model.predict(tomorrow_df[features])
    predicted = max(0, float(prediction[0]))
    log.info(f"[{mid_code}] 예측된 내일 판매량: {predicted:.2f}개")
    return predicted


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
    최근 품절 이력을 고려해 품절 제품을 제외하거나 우선순위를 낮춥니다.
    소수점 이하가 있을 경우 데이터 부족 상품을 추가로 추천합니다.
    """
    if not db_path.exists():
        log.warning(f"Database not found at {db_path}. Cannot generate recommendations.")
        return []

    with sqlite3.connect(db_path) as conn:
        query = """
            SELECT
                product_code,
                product_name,
                SUM(sales) as total_sales
            FROM mid_sales
            WHERE mid_code = ?
            GROUP BY product_code, product_name
            HAVING SUM(sales) > 0
        """
        sales_by_product = pd.read_sql(query, conn, params=(mid_code,))

        # 최근 품절 이력 조회
        lookback_days = 7
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        stockout_query = """
            SELECT
                product_code,
                SUM(CASE WHEN stock = 0 THEN 1 ELSE 0 END) AS stockout_count,
                COUNT(*) AS total_days
            FROM mid_sales
            WHERE mid_code = ?
              AND DATE(collected_at) >= ?
            GROUP BY product_code
        """
        stockout_df = pd.read_sql(stockout_query, conn, params=(mid_code, start_date))

    if sales_by_product.empty:
        log.warning(f"[{mid_code}] No sales data found for any products. Cannot make recommendations. Returning empty list.")
        return []

    # 품절률 계산 및 필터링
    sales_by_product = sales_by_product.merge(stockout_df, on="product_code", how="left")
    sales_by_product[["stockout_count", "total_days"]] = sales_by_product[["stockout_count", "total_days"]].fillna(0)
    sales_by_product["stockout_rate"] = sales_by_product.apply(
        lambda r: r["stockout_count"] / r["total_days"] if r["total_days"] > 0 else 0,
        axis=1,
    )
    # stockout_threshold = 0.5 # 품절률 기반 필터링 로직 제거
    # sales_by_product = sales_by_product[sales_by_product["stockout_rate"] < stockout_threshold] # 품절률 기반 필터링 로직 제거
    if sales_by_product.empty:
        log.warning(f"[{mid_code}] All products filtered out due to high stockout rates. Returning empty list.")
        return []

    sales_by_product = sales_by_product.sort_values(by="total_sales", ascending=False).reset_index(drop=True)

    total_sales_sum = sales_by_product["total_sales"].sum()
    if total_sales_sum == 0:
        log.warning(f"[{mid_code}] Total sales sum is zero. Cannot calculate ratios. Distributing evenly.")
        sales_by_product["ratio"] = 1 / len(sales_by_product)
    else:
        sales_by_product["ratio"] = sales_by_product["total_sales"] / total_sales_sum

    # 품절률을 반영한 비율 조정 (품절률이 높을수록 가중치 부여)
    sales_by_product["ratio"] = sales_by_product["ratio"] * (1 + sales_by_product["stockout_rate"])
    sales_by_product["ratio"] = sales_by_product["ratio"] / sales_by_product["ratio"].sum()

    product_ratio_map = dict(zip(sales_by_product["product_code"], sales_by_product["ratio"]))

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
        row = sales_by_product[sales_by_product["product_code"] == prod_code].iloc[0]
        # 최소 1개 추천 보장
        final_quantity = max(1, data["recommended_quantity"])
        reason = (
            "percentage_based"
            if row["total_sales"] >= 10
            else "data_gathering_or_percentage_based"
        )
        if row["stockout_rate"] > 0:
            reason = "stockout_adjusted"
        final_recommendations.append(
            {
                "product_code": prod_code,
                "product_name": data["product_name"],
                "recommended_quantity": int(final_quantity),
                "stockout_rate": float(row["stockout_rate"]),
                "reason": reason,
            }
        )

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

    model_dir = Path(__file__).resolve().parent / "tuned_models"

    logger = get_logger(__name__, level=logging.DEBUG, store_id=store_name)
    logger.info(f"[{store_name}] 모든 카테고리 예측 시작...")

    with sqlite3.connect(sales_db_path) as conn:
        mid_categories = pd.read_sql("SELECT DISTINCT mid_code, mid_name FROM mid_sales", conn)

    prediction_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    target_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    with sqlite3.connect(prediction_db_path) as conn:
        cursor = conn.cursor()
        for index, row in mid_categories.iterrows():
            mid_code = row['mid_code']
            mid_name = row['mid_name']

            training_data = get_training_data_for_category(sales_db_path, mid_code)
            predicted_sales = train_and_predict(
                mid_code, training_data, model_dir=model_dir
            )

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