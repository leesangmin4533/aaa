import logging
import os
from pathlib import Path
from datetime import datetime
import json

# -------------------------------------------------------------------
# 각 기능 모듈에서 필요한 함수들을 가져옵니다.
# -------------------------------------------------------------------

# 자동화 워크플로우 및 드라이버 설정
from automation.driver import create_driver

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

from selenium.webdriver.support.ui import WebDriverWait

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
SCRIPTS_DIR = str(ROOT_DIR / "scripts") # 올바른 scripts 폴더 경로

# 자바스크립트 파일 내용 로드
with open(Path(SCRIPTS_DIR) / "nexacro_automation_library.js", "r", encoding="utf-8") as f:
    NEXACRO_AUTOMATION_LIBRARY_JS = f.read()

with open(Path(SCRIPTS_DIR) / "navigation.js", "r", encoding="utf-8") as f:
    NAVIGATION_JS = f.read()


def main():
    """
    메인 실행 함수: 로그인, 데이터 수집, 예측의 전체 과정을 조율합니다.
    """
    log.info("===== 전체 자동화 프로세스를 시작합니다. =====", extra={'tag': 'main'})

    DB_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    driver = None
    try:
        # -----------------------------------------------------------------
        # 1. 드라이버 초기화 및 로그인
        # -----------------------------------------------------------------
        log.info(">>> [1단계] 드라이버 초기화 및 로그인합니다.", extra={'tag': 'main'})
        driver = create_driver()
        if not login_bgf(driver, credential_path=CREDENTIAL_PATH):
            log.critical("로그인에 실패했습니다. 프로세스를 종료합니다.", extra={'tag': 'main'})
            return
        log.info("<<< [1단계] 로그인 성공.", extra={'tag': 'main'})

        # -----------------------------------------------------------------
        # 2. Nexacro 자동화 라이브러리 주입 및 네비게이션
        # -----------------------------------------------------------------
        log.info(">>> [2단계] Nexacro 자동화 라이브러리 주입 및 네비게이션을 시작합니다.", extra={'tag': 'main'})
        # Nexacro 자동화 라이브러리 주입
        driver.execute_script(NEXACRO_AUTOMATION_LIBRARY_JS)
        log.info("Nexacro 자동화 라이브러리 주입 완료.", extra={'tag': 'main'})

        # 네비게이션 스크립트 실행 (매출분석 -> 중분류별 매출 구성비)
        driver.execute_script(NAVIGATION_JS)
        log.info("네비게이션 스크립트 실행 완료.", extra={'tag': 'main'})

        # -----------------------------------------------------------------
        # 3. 중분류 매출 데이터 수집
        # -----------------------------------------------------------------
        log.info(">>> [3단계] 중분류 매출 데이터 수집을 시작합니다.", extra={'tag': 'main'})
        today_yyyymmdd = datetime.now().strftime("%Y%m%d")
        
        # runCollectionForDate 함수 호출 및 완료 대기
        # 이 함수는 Promise를 반환하므로, Promise가 해결될 때까지 기다려야 합니다.
        # Selenium의 execute_script는 Promise를 직접 기다리지 않으므로,
        # JS 내부에서 완료를 알리는 플래그나 데이터를 설정하도록 해야 합니다.
        # nexacro_automation_library.js는 window.automation.isCollecting 플래그를 사용합니다.
        
        # 데이터 수집 시작
        driver.execute_script(f"window.automation.runCollectionForDate('{today_yyyymmdd}')")
        log.info(f"runCollectionForDate('{today_yyyymmdd}') 호출 완료. 데이터 수집 완료를 대기합니다.", extra={'tag': 'main'})

        # 데이터 수집 완료 대기 (최대 5분)
        WebDriverWait(driver, 300).until(
            lambda d: d.execute_script("return !window.automation.isCollecting")
        )
        log.info("데이터 수집 완료 플래그 확인.", extra={'tag': 'main'})

        # 수집된 데이터 가져오기
        collected_data = driver.execute_script("return window.automation.parsedData")
        
        # JavaScript 내부 오류 및 로그 가져오기
        js_errors = driver.execute_script("return window.automation.errors")
        js_logs = driver.execute_script("return window.automation.logs")

        if js_errors:
            log.error(f"JavaScript 내부 오류 발생: {js_errors}", extra={'tag': 'main'})
        if js_logs:
            log.info(f"JavaScript 내부 로그: {js_logs}", extra={'tag': 'main'})
        
        if collected_data:
            log.info(f"총 {len(collected_data)}개의 중분류 매출 데이터를 수집했습니다.", extra={'tag': 'main'})
            # 수집된 데이터를 DB에 저장
            # save_to_db 함수는 records와 db_path를 인자로 받습니다.
            # collected_data는 이미 save_to_db가 기대하는 형식과 유사할 것으로 예상됩니다.
            # 필요하다면 여기서 collected_data를 save_to_db 형식에 맞게 변환해야 합니다.
            # 현재 collected_data는 list of dicts 형태이므로 바로 전달합니다.
            from automation.workflow import save_to_db # save_to_db 함수를 여기서 import
            inserted_count = save_to_db(collected_data, DB_PATH)
            log.info(f"수집된 데이터를 {DB_PATH}에 저장했습니다. {inserted_count}개 레코드 삽입.", extra={'tag': 'main'})
        else:
            log.warning("수집된 중분류 매출 데이터가 없습니다.", extra={'tag': 'main'})
            # 데이터 수집 실패 시 예측을 진행할 수 없으므로 프로세스 종료
            return

        log.info("<<< [3단계] 중분류 매출 데이터 수집 및 저장이 성공적으로 완료되었습니다.", extra={'tag': 'main'})

    except Exception as e:
        log.critical(f"자동화 프로세스 중 심각한 오류가 발생했습니다: {e}", exc_info=True, extra={'tag': 'main'})
        return
    finally:
        if driver:
            log.info("드라이버를 종료합니다.", extra={'tag': 'main'})
            driver.quit()

    # -----------------------------------------------------------------
    # 4. 주먹밥 판매량 예측
    # -----------------------------------------------------------------
    if JUMEKBAP_MODULE_AVAILABLE:
        log.info(">>> [4단계] 주먹밥 판매량 예측을 시작합니다.", extra={'tag': 'main'})
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

            log.info("<<< [4단계] 주먹밥 판매량 예측이 성공적으로 완료되었습니다.", extra={'tag': 'main'})

        except Exception as e:
            log.error(f"주먹밥 판매량 예측 중 오류가 발생했습니다: {e}", exc_info=True, extra={'tag': 'main'})
    else:
        log.warning("'analysis.jumeokbap_prediction' 모듈을 찾을 수 없어 예측 단계를 건너뜁니다.", extra={'tag': 'main'})

    log.info("===== 모든 자동화 프로세스가 종료되었습니다. =====", extra={'tag': 'main'})


if __name__ == "__main__":
    if not (ROOT_DIR / ".env").exists():
        log.warning("'.env' 파일이 프로젝트 루트에 존재하지 않습니다. BGF_USER_ID, BGF_PASSWORD 환경 변수가 설정되어 있어야 합니다.", extra={'tag': 'main'})
        
    main()
