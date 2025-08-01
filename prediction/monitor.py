import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import logging
from pathlib import Path

log = logging.getLogger(__name__)

def init_performance_db(db_path: Path):
    """모델 예측 성능 기록을 위한 DB 테이블을 초기화합니다."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS prediction_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evaluation_date TEXT,   -- 성능 평가를 수행한 날짜 (오늘)
            target_date TEXT,       -- 평가 대상 날짜 (어제)
            mid_code TEXT,          -- 중분류 코드
            predicted_sales REAL,   -- 어제 예측했던 판매량
            actual_sales REAL,      -- 어제의 실제 판매량
            error_rate_percent REAL,-- 오차율 (%)
            UNIQUE(target_date, mid_code)
        )
        """)
        conn.commit()

def update_performance_log(sales_db_path: Path, prediction_db_path: Path):
    """어제의 예측 성능을 계산하고 DB에 기록합니다."""
    store_name = sales_db_path.stem
    log.info(f"[{store_name}] 모델 성능 모니터링 시작...")

    init_performance_db(prediction_db_path)

    yesterday = datetime.now().date() - timedelta(days=1)
    yesterday_str = yesterday.strftime("%Y-%m-%d")
    evaluation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with sqlite3.connect(sales_db_path) as sales_conn:
            # 어제의 실제 판매량 가져오기
            actual_sales_df = pd.read_sql(
                f"SELECT mid_code, SUM(sales) as actual_sales FROM mid_sales WHERE SUBSTR(collected_at, 1, 10) = '{yesterday_str}' GROUP BY mid_code",
                sales_conn
            )
        
        if actual_sales_df.empty:
            log.warning(f"[{store_name}] 어제({yesterday_str})의 실제 판매 데이터가 없어 성능 평가를 건너뜁니다.")
            return

        with sqlite3.connect(prediction_db_path) as pred_conn:
            # 어제 예측했던 판매량 가져오기
            predicted_sales_df = pd.read_sql(
                f"SELECT mid_code, predicted_sales FROM category_predictions WHERE target_date = '{yesterday_str}'",
                pred_conn
            )

        if predicted_sales_df.empty:
            log.warning(f"[{store_name}] 어제({yesterday_str})에 대한 예측 데이터가 없어 성능 평가를 건너뜁니다.")
            return

        # 실제 판매량과 예측 판매량 병합
        merged_df = pd.merge(actual_sales_df, predicted_sales_df, on='mid_code', how='left')
        merged_df['predicted_sales'] = merged_df['predicted_sales'].fillna(0) # 예측값이 없는 경우 0으로 채움

        performance_records = []
        for index, row in merged_df.iterrows():
            mid_code = row['mid_code']
            actual = row['actual_sales']
            predicted = row['predicted_sales']

            error_rate = 0.0
            if actual != 0:
                error_rate = abs(actual - predicted) / actual * 100
            elif predicted != 0: # 실제 판매량은 0인데 예측은 0이 아닌 경우
                error_rate = 100.0 # 100% 오차
            
            performance_records.append({
                'evaluation_date': evaluation_date,
                'target_date': yesterday_str,
                'mid_code': mid_code,
                'predicted_sales': predicted,
                'actual_sales': actual,
                'error_rate_percent': error_rate
            })
        
        with sqlite3.connect(prediction_db_path) as conn:
            cursor = conn.cursor()
            insert_sql = """
            INSERT OR REPLACE INTO prediction_performance 
            (evaluation_date, target_date, mid_code, predicted_sales, actual_sales, error_rate_percent)
            VALUES (:evaluation_date, :target_date, :mid_code, :predicted_sales, :actual_sales, :error_rate_percent)
            """
            cursor.executemany(insert_sql, performance_records)
            conn.commit()

        log.info(f"[{store_name}] 모델 성능 평가 완료. {len(performance_records)}개 중분류 기록.")

    except Exception as e:
        log.error(f"[{store_name}] 모델 성능 모니터링 중 오류 발생: {e}", exc_info=True)
