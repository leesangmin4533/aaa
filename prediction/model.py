import sqlite3
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import holidays
import requests
import logging
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import random
import heapq

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

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
    nx, ny = 60, 127 

    for date in dates:
        base_date_str = date.strftime('%Y%m%d')
        now = datetime.now()
        base_time_str = now.strftime('%H00')

        url = f"https://apihub.kma.go.kr/api/typ02/openApi/VilageFcstInfoService_2.0/getUltraSrtNcst?pageNo=1&numOfRows=1000&dataType=JSON&base_date={base_date_str}&base_time={base_time_str}&nx={nx}&ny={ny}&authKey={api_key}"
        
        try:
            response = requests.get(url, timeout=10) # Added timeout of 10 seconds
            response.raise_for_status() # HTTP 오류 (4xx, 5xx) 발생 시 예외 처리
            data = response.json()
            log.debug(f"Weather API raw response for {date}: {json.dumps(data, indent=2)}")
            
            avg_temp = 0.0
            total_rainfall = 0.0
            
            items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
            log.debug(f"Weather API parsed items for {date}: {items}")

            for item in items:
                category = item.get('category')
                obsr_value = item.get('obsrValue')
                if category == 'T1H':
                    try: avg_temp = float(obsr_value)
                    except (ValueError, TypeError): pass
                elif category == 'RN1':
                    try: total_rainfall = float(obsr_value)
                    except (ValueError, TypeError): pass
            weather_data.append({'date': date, 'temperature': avg_temp, 'rainfall': total_rainfall})
        except requests.exceptions.Timeout:
            log.error(f"{date} 날씨 데이터 요청 중 타임아웃 발생. 기본값으로 대체합니다.", exc_info=True)
            weather_data.append({'date': date, 'temperature': 15, 'rainfall': 0}) # Fallback values
        except requests.exceptions.RequestException as e:
            log.error(f"{date} 날씨 데이터 요청 중 오류: {e}. 기본값으로 대체합니다.", exc_info=True)
            weather_data.append({'date': date, 'temperature': 15, 'rainfall': 0}) # Fallback values
        except Exception as e:
            log.error(f"{dt} 날씨 데이터 파싱 중 예상치 못한 오류: {e}. 기본값으로 대체합니다.", exc_info=True)
            weather_data.append({'date': date, 'temperature': 15, 'rainfall': 0}) # Fallback values

    return pd.DataFrame(weather_data)

def get_training_data_for_category(db_path: Path, mid_code: str) -> pd.DataFrame:
    """특정 중분류의 판매 데이터를 DB에서 읽어와 날짜 특성을 추가합니다."""
    if not db_path.exists():
        return pd.DataFrame()

    with sqlite3.connect(db_path) as conn:
        query = f"SELECT collected_at, SUM(sales) as total_sales FROM mid_sales WHERE mid_code = '{mid_code}' GROUP BY SUBSTR(collected_at, 1, 10)"
        df = pd.read_sql(query, conn)

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
    X = df[features]
    y = df[target]

    model = RandomForestRegressor(n_estimators=100, random_state=42)
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
    log.info(f"[{mid_code}] Predicted: {predicted_sales:.2f}. Recommended {len(final_recommendations)} types of items with total quantity of {total_recommended_quantity}.")
    log.info(f"[{mid_code}] Recommendation details: {final_recommendations}")

    return final_recommendations
