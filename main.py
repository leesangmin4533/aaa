import logging
import os
from pathlib import Path

# -------------------------------------------------------------------
# 각 기능 모듈에서 필요한 함수들을 가져옵니다.
# -------------------------------------------------------------------

# 자동화 워크플로우 및 드라이버 설정
from automation.workflow import run_mid_category_collection, save_to_db
from automation.driver import create_chrome_driver
from automation.scripts import collect_mid_category_data

# 로그인 및 팝업 처리
from login.login_bgf import login_bgf

# 주먹밥 판매량 예측
# (이 모듈은 현재 파일 시스템에서 찾을 수 없으므로, 실제 실행 시
# 해당 모듈이 파이썬 경로에 존재해야 합니다.)
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
# 프로젝트 루트 디렉터리를 기준으로 경로를 설정합니다.
ROOT_DIR = Path(__file__).resolve().parent

# .env 파일에서 자격 증명을 사용하므로, 별도 경로를 지정하지 않습니다.
CREDENTIAL_PATH = None 

# 데이터가 저장될 SQLite DB 경로 설정
# 이전에 수정한 'db' 폴더를 사용하도록 경로를 지정합니다.
DB_OUTPUT_DIR = ROOT_DIR / "code_outputs" / "db"
DB_PATH = DB_OUTPUT_DIR / "integrated_sales.db"

# 자바스크립트 스크립트가 있는 디렉터리
SCRIPTS_DIR = str(ROOT_DIR / "automation" / "scripts")


def main():
    """
    메인 실행 함수: 로그인, 데이터 수집, 예측의 전체 과정을 조율합니다.
    """
    log.info("===== 전체 자동화 프로세스를 시작합니다. =====")

    # 데이터베이스 디렉터리가 없으면 생성
    DB_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------
    # 1. 중분류 매출 데이터 수집
    # -----------------------------------------------------------------
    try:
        log.info(">>> [1단계] 중분류 매출 데이터 수집을 시작합니다.")
        # run_mid_category_collection 워크플로우 실행
        # 이 함수는 내부적으로 드라이버 생성, 로그인, 데이터 수집, 저장을 모두 처리합니다.
        run_mid_category_collection(
            cred_path=CREDENTIAL_PATH,
            create_driver_func=create_chrome_driver,
            login_func=login_bgf,
            collect_mid_category_data_func=collect_mid_category_data,
            save_path=DB_PATH,
            scripts_dir=SCRIPTS_DIR
        )
        log.info("<<< [1단계] 중분류 매출 데이터 수집이 성공적으로 완료되었습니다.")

    except Exception as e:
        log.critical(f"데이터 수집 단계에서 심각한 오류가 발생했습니다: {e}", exc_info=True)
        # 데이터 수집 실패 시 예측을 진행할 수 없으므로 프로세스 종료
        return

    # -----------------------------------------------------------------
    # 2. 주먹밥 판매량 예측
    # -----------------------------------------------------------------
    if JUMEKBAP_MODULE_AVAILABLE:
        log.info(">>> [2단계] 주먹밥 판매량 예측을 시작합니다.")
        try:
            # get_configured_db_path 함수 대신, 위에서 정의한 DB_PATH를 사용합니다.
            # 이 부분이 원래 코드와 달라지는 핵심입니다.
            db_path_for_prediction = str(DB_PATH)
            
            log.info(f"예측을 위해 다음 데이터베이스를 사용합니다: {db_path_for_prediction}")

            tomorrow_forecast = predict_jumeokbap_quantity(db_path_for_prediction)
            mix_recommendations = recommend_product_mix(db_path_for_prediction)

            log.info("--- 예측 결과 ---")
            log.info(f"예상 주문량: {tomorrow_forecast:.2f}개")
            log.info(f"추천 상품 조합: {mix_recommendations}")
            log.info("-----------------")
            
            # 콘솔에도 보기 쉽게 출력
            print("
--- 예측 결과 ---")
            print(f"예상 주문량: {tomorrow_forecast:.2f}개")
            print(f"추천 상품 조합: {mix_recommendations}")
            print("-----------------")

            log.info("<<< [2단계] 주먹밥 판매량 예측이 성공적으로 완료되었습니다.")

        except Exception as e:
            log.error(f"주먹밥 판매량 예측 중 오류가 발생했습니다: {e}", exc_info=True)
    else:
        log.warning("'analysis.jumeokbap_prediction' 모듈을 찾을 수 없어 예측 단계를 건너뜁니다.")

    log.info("===== 모든 자동화 프로세스가 종료되었습니다. =====")


if __name__ == "__main__":
    # .env 파일이 프로젝트 루트에 있는지 확인하고 로드
    if not (ROOT_DIR / ".env").exists():
        log.warning("'.env' 파일이 프로젝트 루트에 존재하지 않습니다. BGF_USER_ID, BGF_PASSWORD 환경 변수가 설정되어 있어야 합니다.")
        
    main()