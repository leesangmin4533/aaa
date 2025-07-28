

import logging
from analysis.jumeokbap_prediction import (
    get_configured_db_path,
    predict_jumeokbap_quantity,
    recommend_product_mix,
)

# 로그 메시지 포맷 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    주먹밥 판매량을 예측하고 상품 조합을 추천하는 메인 함수
    """
    try:
        logging.info("데이터베이스 경로를 설정합니다.")
        db_path = get_configured_db_path()

        if not db_path:
            logging.error("데이터베이스 경로를 찾을 수 없습니다.")
            return

        logging.info(f"\'{db_path}\' 경로의 데이터베이스를 사용하여 예측을 시작합니다.")
        
        tomorrow_forecast = predict_jumeokbap_quantity(db_path)
        mix_recommendations = recommend_product_mix(db_path)

        print("\n--- 예측 결과 ---")
        print(f"예상 주문량: {tomorrow_forecast:.2f}개")
        print(f"추천 상품 조합: {mix_recommendations}")
        print("-----------------")

    except FileNotFoundError:
        logging.error(f"오류: 데이터베이스 파일을 찾을 수 없습니다. 경로: {db_path}")
    except Exception as e:
        logging.error(f"예측 처리 중 예기치 않은 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()

