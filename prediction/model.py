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
            weather_data.append({'date': dt, 'temperature': 15, 'rainfall': 0}) # Fallback values
        except requests.exceptions.RequestException as e:
            log.error(f"{date} 날씨 데이터 요청 중 오류: {e}. 기본값으로 대체합니다.", exc_info=True)
            weather_data.append({'date': dt, 'temperature': 15, 'rainfall': 0}) # Fallback values
        except Exception as e:
            log.error(f"{dt} 날씨 데이터 파싱 중 예상치 못한 오류: {e}. 기본값으로 대체합니다.", exc_info=True)
            weather_data.append({'date': dt, 'temperature': 15, 'rainfall': 0}) # Fallback values

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
        df = pd.read_sql(query, conn)

    if df.empty:
        log.warning(f"[{mid_code}] No sales data found for any products. Cannot make recommendations. Returning empty list.")
        return []

    final_recommendations = [] # Initialize final_recommendations here

    df = df.sort_values(by='total_sales', ascending=False).reset_index(drop=True)

    total_sales_sum = df['total_sales'].sum()
    if total_sales_sum == 0:
        log.warning(f"[{mid_code}] Total sales sum is zero. Cannot calculate ratios. Distributing evenly.")
        df['ratio'] = 1 / len(df)
    else:
        df['ratio'] = df['total_sales'] / total_sales_sum

    recommendations_map = {} # product_code: {product_name, recommended_quantity}

    # 1. 예측 수량의 정수 부분 배분
    integer_part_to_distribute = int(predicted_sales)
    
    # 각 상품에 할당될 기본 수량 계산
    for _, row in df.iterrows():
        product_code = row['product_code']
        product_name = row['product_name']
        # round() 함수를 사용하여 반올림
        quantity = round(integer_part_to_distribute * row['ratio'])
        if quantity > 0:
            recommendations_map[product_code] = {'product_name': product_name, 'recommended_quantity': quantity}
    
    # 배분된 총 수량과 예측 수량의 정수 부분 비교 및 조정
    current_distributed_sum = sum(item['recommended_quantity'] for item in recommendations_map.values())
    difference = integer_part_to_distribute - current_distributed_sum

    if difference != 0:
        # 차이만큼 수량 조정 (가장 비율이 높은 상품부터)
        sorted_products = sorted(recommendations_map.items(), key=lambda item: df[df['product_code'] == item[0]]['ratio'].iloc[0], reverse=True)
        
        for i in range(abs(difference)):
            if difference > 0: # 더 추가해야 할 경우
                if sorted_products:
                    prod_code = sorted_products[i % len(sorted_products)][0]
                    recommendations_map[prod_code]['recommended_quantity'] += 1
            else: # 더 줄여야 할 경우
                if sorted_products:
                    prod_code = sorted_products[len(sorted_products) - 1 - (i % len(sorted_products))][0] # 가장 비율이 낮은 상품부터
                    if recommendations_map[prod_code]['recommended_quantity'] > 1: # 최소 1개는 유지
                        recommendations_map[prod_code]['recommended_quantity'] -= 1
                    else: # 1개밖에 없으면 다른 상품에서 줄임
                        # 이 경우는 복잡해지므로, 일단 1개 미만으로 줄이지 않도록 함.
                        # 실제 운영에서는 이런 미세 조정이 필요할 수 있음.
                        pass

    # 2. 소수점 이하가 있을 경우 데이터 부족 상품 추가
    has_fractional_part = (predicted_sales - integer_part_to_distribute) > 0.01 # 0.01은 부동소수점 오차 고려
    if has_fractional_part:
        unpopular_products_df = df[df['total_sales'] < 10]
        
        chosen_product = None
        if not unpopular_products_df.empty:
            # 이미 추천된 상품이 아닌 데이터 부족 상품 중에서 랜덤 선택
            available_unpopular = unpopular_products_df[~unpopular_products_df['product_code'].isin(recommendations_map.keys())]
            if not available_unpopular.empty:
                chosen_product = available_unpopular.sample(n=1).iloc[0]
            else: # 모든 데이터 부족 상품이 이미 추천된 경우, 그냥 데이터 부족 상품 중에서 랜덤 선택
                chosen_product = unpopular_products_df.sample(n=1).iloc[0]
        
        if chosen_product is None and not df.empty: # 데이터 부족 상품이 없거나 선택할 수 없는 경우, 전체 상품 중에서 랜덤 선택
            available_products = df[~df['product_code'].isin(recommendations_map.keys())]
            if not available_products.empty:
                chosen_product = available_products.sample(n=1).iloc[0]
            else: # 모든 상품이 이미 추천된 경우, 그냥 전체 상품 중에서 랜덤 선택
                chosen_product = df.sample(n=1).iloc[0]

        if chosen_product is not None and not chosen_product.empty:
            prod_code = chosen_product['product_code']
            prod_name = chosen_product['product_name']
            if prod_code in recommendations_map:
                recommendations_map[prod_code]['recommended_quantity'] += 1
            else:
                recommendations_map[prod_code] = {'product_name': prod_name, 'recommended_quantity': 1}
            log.debug(f"[{mid_code}] Added 1 additional item ({prod_name}) due to fractional part.")

    final_recommendations = []
    for prod_code, data in recommendations_map.items():
        # 최소 1개 추천 보장
        final_quantity = max(1, data['recommended_quantity'])
        final_recommendations.append({
            "product_code": prod_code,
            "product_name": data["product_name"],
            "recommended_quantity": int(final_quantity),
            "reason": "percentage_based" if df[df['product_code'] == prod_code]['total_sales'].iloc[0] >= 10 else "data_gathering_or_percentage_based"
        })
    
    # 최종 추천 수량 합계 로깅
    total_recommended_quantity = sum(rec['recommended_quantity'] for rec in final_recommendations)
    log.info(f"[{mid_code}] Predicted: {predicted_sales:.2f}. Recommended {len(final_recommendations)} types of items with total quantity of {total_recommended_quantity}.")
    log.info(f"[{mid_code}] Recommendation details: {final_recommendations}")
    
    return final_recommendations
