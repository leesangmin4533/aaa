import sqlite3
import pandas as pd
from pathlib import Path
import logging

# 프로젝트의 다른 모듈을 가져오기 위해 경로 설정
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prediction.xgboost import get_training_data_for_category, train_model_for_category
from utils.log_util import get_logger

# --- 설정 --- #
# 학습할 데이터베이스 파일들이 있는 디렉토리
DB_DIR = Path(__file__).resolve().parent / "code_outputs" / "db"
# 학습된 모델을 저장할 디렉토리
MODEL_DIR = Path(__file__).resolve().parent / "prediction" / "tuned_models"


def main():
    """DB_DIR에 있는 모든 데이터베이스를 순회하며, 각 카테고리별 모델을 재학습합니다."""
    logger = get_logger("model_training", level=logging.INFO)
    logger.info("모델 재학습 파이프라인을 시작합니다.")

    # .db 확장자를 가진 모든 데이터베이스 파일을 찾음
    db_files = list(DB_DIR.glob("*.db"))
    
    if not db_files:
        logger.warning(f"{DB_DIR}에서 학습할 데이터베이스 파일을 찾을 수 없습니다.")
        return

    for db_path in db_files:
        store_name = db_path.stem
        logger.info(f"--- {store_name} 매장 모델 학습 시작 ---")

        try:
            with sqlite3.connect(db_path) as conn:
                # 학습할 모든 중분류 카테고리 목록을 가져옴
                mid_categories = pd.read_sql("SELECT DISTINCT mid_code FROM mid_sales", conn)
            
            logger.info(f"{store_name} 매장에서 {len(mid_categories)}개의 카테리에 대한 학습을 진행합니다.")

            for mid_code in mid_categories['mid_code']:
                # 1. 특정 카테고리의 전체 학습 데이터를 가져옴
                training_data = get_training_data_for_category(db_path, mid_code)
                
                if training_data.empty:
                    logger.warning(f"[{store_name}/{mid_code}] 학습 데이터가 없어 건너뜁니다.")
                    continue

                # 2. 모델을 학습하고 .pkl 파일로 저장
                train_model_for_category(mid_code, training_data, MODEL_DIR)

            logger.info(f"--- {store_name} 매장 모델 학습 완료 ---")

        except Exception as e:
            logger.error(f"{store_name} 매장 모델 학습 중 오류 발생: {e}", exc_info=True)

    logger.info("모든 매장에 대한 모델 재학습 파이프라인이 종료되었습니다.")

if __name__ == "__main__":
    main()
