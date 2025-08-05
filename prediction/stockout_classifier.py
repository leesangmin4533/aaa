import sqlite3
from pathlib import Path
import pandas as pd
import xgboost


def build_training_data(db_path: Path, mid_code: str) -> pd.DataFrame:
    """mid_sales 테이블을 기반으로 품절 예측 학습 데이터를 생성합니다."""
    if not db_path.exists():
        return pd.DataFrame()
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql(
            "SELECT collected_at, product_code, sales, stock FROM mid_sales WHERE mid_code = ?",
            conn,
            params=(mid_code,),
        )
    if df.empty:
        return pd.DataFrame()
    df['date'] = pd.to_datetime(df['collected_at']).dt.date
    df.sort_values(['product_code', 'date'], inplace=True)
    df['next_day_sales'] = df.groupby('product_code')['sales'].shift(-1).fillna(0)
    df['will_stockout'] = (df['stock'] - df['next_day_sales'] < 0).astype(int)
    df = df.rename(columns={'stock': 'current_stock', 'next_day_sales': 'predicted_demand'})
    return df[['current_stock', 'predicted_demand', 'will_stockout']]


def train_classifier(training_df: pd.DataFrame) -> xgboost.XGBClassifier:
    """주어진 학습 데이터로 XGBoost 분류 모델을 학습합니다."""
    if training_df.empty:
        raise ValueError("training_df is empty")
    X = training_df[['current_stock', 'predicted_demand']].astype('float32')
    y = training_df['will_stockout'].astype('int')
    model = xgboost.XGBClassifier(
        random_state=42, use_label_encoder=False, eval_metric='logloss'
    )
    model.fit(X, y)
    return model


def predict_stockout_probability(
    model: xgboost.XGBClassifier, current_stock: float, predicted_demand: float
) -> float:
    """품절 확률을 예측합니다."""
    df = pd.DataFrame(
        [{'current_stock': current_stock, 'predicted_demand': predicted_demand}]
    )
    prob = model.predict_proba(df)[0][1]
    return float(prob)
