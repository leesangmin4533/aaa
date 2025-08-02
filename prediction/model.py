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
            response = requests.get(url)
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
        except Exception as e:
            log.error(f"{date} 날씨 데이터 요청/파싱 중 오류: {e}", exc_info=True)
            weather_data.append({'date': date, 'temperature': 0, 'rainfall': 0})

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
    예측된 총 판매량을 기반으로 인기 상품과 데이터 부족 상품을 조합하여 추천합니다.
    - 정수 부: 가장 인기 있는 상품으로 추천
    - 소수 부: 판매 데이터가 적은 상품을 추천하여 데이터 수집을 유도
    - 잔여 수량: 추천된 상품들의 판매량 비율에 따라 잔여 수량을 배분
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
        log.warning(f"[{mid_code}] No sales data found for any products. Cannot make recommendations.")
        return []

    df = df.sort_values(by='total_sales', ascending=False).reset_index(drop=True)

    insufficient_data_threshold = 10
    popular_products_df = df[df['total_sales'] >= insufficient_data_threshold]
    unpopular_products_df = df[df['total_sales'] < insufficient_data_threshold]

    recommendations = []
    base_recommendations = []
    num_popular_to_recommend = int(predicted_sales)
    has_fractional_part = (predicted_sales - num_popular_to_recommend) > 0.01

    actual_popular_to_recommend = min(num_popular_to_recommend, len(popular_products_df))
    if actual_popular_to_recommend > 0:
        top_popular_df = popular_products_df.head(actual_popular_to_recommend)
        for _, row in top_popular_df.iterrows():
            base_recommendations.append(row.to_dict())

    if has_fractional_part:
        unpopular_products_to_choose_from = unpopular_products_df[
            ~unpopular_products_df['product_code'].isin([rec['product_code'] for rec in base_recommendations])
        ]
        if not unpopular_products_to_choose_from.empty:
            chosen_unpopular = unpopular_products_to_choose_from.sample(n=1)
            base_recommendations.append(chosen_unpopular.iloc[0].to_dict())
        else:
            remaining_popular_products = popular_products_df[
                ~popular_products_df['product_code'].isin([rec['product_code'] for rec in base_recommendations])
            ]
            if not remaining_popular_products.empty:
                next_popular = remaining_popular_products.head(1)
                base_recommendations.append(next_popular.iloc[0].to_dict())

    if not base_recommendations:
        log.warning(f"[{mid_code}] Could not form a base recommendation list.")
        return []

    recommended_df = pd.DataFrame(base_recommendations)
    total_sales_of_recommended = recommended_df['total_sales'].sum()

    if total_sales_of_recommended == 0:
        # 모든 추천 상품의 판매량이 0일 경우, 균등하게 배분
        log.warning(f"[{mid_code}] Total sales of recommended items is zero. Distributing quantity evenly.")
        recommended_df['ratio'] = 1 / len(recommended_df)
    else:
        recommended_df['ratio'] = recommended_df['total_sales'] / total_sales_of_recommended

    # 각 상품에 기본 1개씩 할당하고 남은 잔여 수량 계산
    initial_assigned_quantity = len(recommended_df)
    remaining_quantity = predicted_sales - initial_assigned_quantity

    # 최종 추천 목록 생성
    for _, row in recommended_df.iterrows():
        # 기본 1개 + 잔여 수량 배분
        additional_quantity = round(remaining_quantity * row['ratio'])
        final_quantity = 1 + additional_quantity
        
        recommendations.append({
            "product_code": row["product_code"],
            "product_name": row["product_name"],
            "recommended_quantity": int(max(1, final_quantity)), # 최소 1개 보장
            "reason": "popular_item" if row['total_sales'] >= insufficient_data_threshold else "data_gathering"
        })

    # 총 추천 수량이 예측 수량과 근사하도록 조정
    total_recommended_quantity = sum(rec['recommended_quantity'] for rec in recommendations)
    if total_recommended_quantity < int(predicted_sales):
        # 예측 수량보다 적게 추천되었을 경우, 가장 인기있는 상품에 수량 추가
        if recommendations:
            recommendations[0]["recommended_quantity"] += int(predicted_sales) - total_recommended_quantity

    log.info(f"[{mid_code}] Predicted: {predicted_sales:.2f}. Recommended {len(recommendations)} types of items with total quantity of {sum(r['recommended_quantity'] for r in recommendations)}.")
    log.info(f"[{mid_code}] Recommendation details: {recommendations}")
    
    return recommendations
