from modules.common.login import run_login
from modules.common.driver import create_chrome_driver
from modules.common.module_map import write_module_map
import json
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_sales_analysis(driver):
    """Execute sales analysis steps defined in mid_category_sales_ssv.json."""
    from modules.common.network import extract_ssv_from_cdp
    from modules.common.login import load_env

    logger.info("진입: run_sales_analysis")
    with open(
        "modules/sales_analysis/mid_category_sales_ssv.json", "r", encoding="utf-8"
    ) as f:
        behavior = json.load(f)["behavior"]

    env = load_env()
    elements = {}

    for step in behavior:
        action = step.get("action")
        log = step.get("log")
        logger.info(f"진행: {action} 시작")
        
        if action == "navigate_menu":
            from modules.sales_analysis.navigate_to_mid_category import navigate_to_mid_category_sales
            navigate_to_mid_category_sales(driver)
        elif action == "click":
            driver.find_element("xpath", step["target_xpath"]).click()
        elif action == "sleep":
            # Allow pauses between actions when server responses are required
            time.sleep(step.get("seconds", 1))
        elif action == "extract_network_response":
            extract_ssv_from_cdp(driver, keyword=step["match"], save_to=step["save_to"])
        elif action == "parse_ssv":
            from modules.data_parser.parse_and_save import parse_ssv, save_filtered_rows
            with open(step["input"], "r", encoding="utf-8") as f:
                rows = parse_ssv(f.read())
            save_filtered_rows(
                rows,
                step["save_to"],
                fields=step.get("fields"),
                filter_dict=step.get("filter"),
            )
        logger.info(f"결과: {action} 완료")
        if log:
            logger.info(log)


def main():
    logger.info("진입: main")

    logger.info("진행: Chrome 드라이버 생성")
    driver = create_chrome_driver()  # ✅ 자동 드라이버 탐색
    logger.info("결과: Chrome 드라이버 생성 완료")

    logger.info("진행: 로그인 시퀀스")
    try:
        run_login(driver)
        logger.info("결과: 로그인 시퀀스 성공")
    except Exception as e:
        logger.exception("결과: 로그인 시퀀스 실패")
        driver.quit()
        raise

    logger.info("진행: 매출 분석")
    try:
        run_sales_analysis(driver)
        logger.info("결과: 매출 분석 성공")
    except Exception as e:
        logger.exception("결과: 매출 분석 실패")
        driver.quit()
        raise

    logger.info("진행: 모듈 맵 저장")
    write_module_map()
    logger.info("결과: 모듈 맵 저장 완료")

    input("⏸ 로그인 화면 유지 중. Enter를 누르면 종료됩니다.")

    logger.info("진행: 드라이버 종료")
    driver.quit()
    logger.info("결과: 드라이버 종료 완료")


if __name__ == "__main__":
    main()
