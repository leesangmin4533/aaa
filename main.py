import logging
import os
from pathlib import Path

# -------------------------------------------------------------------
# 각 기능 모듈에서 필요한 함수들을 가져옵니다.
# -------------------------------------------------------------------

# 자동화 워크플로우 및 드라이버 설정
from automation.workflow import run_mid_category_collection, save_to_db
from automation.driver import create_driver
from automation.scripts import collect_mid_category_data

# 로그인 및 팝업 처리
from login.login_bgf import login_bgf

# 주먹밥 판매량 예측
try:
    from analysis.jumeokbap_prediction import (
        get_configured_db_path,
        predict_jumeokbap_quantity,
        recommend_product_mix,
    )
    JUMEKBAP_MODULE_AVAILABLE = True
except ImportError:
    JUMEKBAP_MODULE_AVAILABLE = False

# 로깅 설정
from utils.log_util import get_logger
log = get_logger(__name__)


# -------------------------------------------------------------------
# 기본 설정 변수
# -------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent
CREDENTIAL_PATH = None 
DB_OUTPUT_DIR = ROOT_DIR / "code_outputs" / "db"
DB_PATH = DB_OUTPUT_DIR / "integrated_sales.db"
SCRIPTS_DIR = str(ROOT_DIR / "automation" / "scripts")


def main():
    """
    메인 실행 함수: 로그인, 데이터 수집, 예측의 전체 과정을 조율합니다.
    """
    log.info("===== 전체 자동화 프로세스를 시작합니다. =====", extra={'tag': 'main'})

    DB_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------
    # 1. 중분류 매출 데이터 수집
    # -----------------------------------------------------------------
    try:
        log.info(">>> [1단계] 중분류 매출 데이터 수집을 시작합니다.", extra={'tag': 'main'})
        run_mid_category_collection(
            cred_path=CREDENTIAL_PATH,
            create_driver_func=create_driver,
            login_func=login_bgf,
            collect_mid_category_data_func=collect_mid_category_data,
            save_path=DB_PATH,
            scripts_dir=SCRIPTS_DIR
        )
        log.info("<<< [1단계] 중분류 매출 데이터 수집이 성공적으로 완료되었습니다.", extra={'tag': 'main'})

    except Exception as e:
        log.critical(f"데이터 수집 단계에서 심각한 오류가 발생했습니다: {e}", exc_info=True, extra={'tag': 'main'})
        return

    # -----------------------------------------------------------------
    # 2. 주먹밥 판매량 예측
    # -----------------------------------------------------------------
    if JUMEKBAP_MODULE_AVAILABLE:
        log.info(">>> [2단계] 주먹밥 판매량 예측을 시작합니다.", extra={'tag': 'main'})
        try:
            db_path_for_prediction = str(DB_PATH)
            log.info(f"예측을 위해 다음 데이터베이스를 사용합니다: {db_path_for_prediction}", extra={'tag': 'main'})

            tomorrow_forecast = predict_jumeokbap_quantity(db_path_for_prediction)
            mix_recommendations = recommend_product_mix(db_path_for_prediction)

            log.info("--- 예측 결과 ---", extra={'tag': 'main'})
            log.info(f"예상 주문량: {tomorrow_forecast:.2f}개", extra={'tag': 'main'})
            log.info(f"추천 상품 조합: {mix_recommendations}", extra={'tag': 'main'})
            log.info("-----------------", extra={'tag': 'main'})
            
            print("\n--- 예측 결과 ---")
            print(f"예상 주문량: {tomorrow_forecast:.2f}개")
            print(f"추천 상품 조합: {mix_recommendations}")
            print("-----------------")

            log.info("<<< [2단계] 주먹밥 판매량 예측이 성공적으로 완료되었습니다.", extra={'tag': 'main'})

        except Exception as e:
            log.error(f"주먹밥 판매량 예측 중 오류가 발생했습니다: {e}", exc_info=True, extra={'tag': 'main'})
    else:
        log.warning("'analysis.jumeokbap_prediction' 모듈을 찾을 수 없어 예측 단계를 건너뜁니다.", extra={'tag': 'main'})

    log.info("===== 모든 자동화 프로세스가 종료되었습니다. =====", extra={'tag': 'main'})


if __name__ == "__main__":
    if not (ROOT_DIR / ".env").exists():
        log.warning("'.env' 파일이 프로젝트 루트에 존재하지 않습니다. BGF_USER_ID, BGF_PASSWORD 환경 변수가 설정되어 있어야 합니다.", extra={'tag': 'main'})
        
    main()