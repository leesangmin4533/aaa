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
    
    return df[['date', 'total_sales', 'weekday', 'month', 'week_of_year', 'is_holiday']]

def train_and_predict(mid_code: str, training_df: pd.DataFrame) -> float:
    """주어진 학습 데이터로 모델을 훈련하고 내일의 판매량을 예측합니다."""
    if training_df.empty or len(training_df) < 7:
        log.warning(f"[{mid_code}] 학습 데이터가 부족하여 기본 예측(Random)을 수행합니다.")
        return random.uniform(10.0, 50.0) # 카테고리별 기본 예측값

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
    """예측된 총 판매량을 기반으로 특정 중분류 내 상품 조합을 추천합니다."""
    if not db_path.exists():
        return []

    with sqlite3.connect(db_path) as conn:
        query = f"SELECT product_code, product_name, SUM(sales) as sales FROM mid_sales WHERE mid_code = '{mid_code}' GROUP BY product_code, product_name"
        df = pd.read_sql(query, conn)

    if df.empty:
        return []

    total_sales_in_category = df['sales'].sum()
    if total_sales_in_category == 0:
        return []
        
    df['ratio'] = df['sales'] / total_sales_in_category
    
    recommendations = []
    for _, row in df.iterrows():
        recommendations.append({
            "product_code": row["product_code"],
            "product_name": row["product_name"],
            "recommended_quantity": int(predicted_sales * row["ratio"])
        })
        
    log.info(f"[{mid_code}] 추천 상품 조합: {recommendations}")
    return recommendations
