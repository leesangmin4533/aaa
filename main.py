from modules.common.login import run_login
from modules.common.driver import create_chrome_driver
from modules.common.module_map import write_module_map
import json
import time
import logging

MODULE_NAME = "main"


def log(step: str, msg: str) -> None:
    logger.info(f"[{MODULE_NAME} > {step}] {msg}")

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

    log("run_sales_analysis", "진입")
    with open(
        "modules/sales_analysis/mid_category_sales_ssv.json", "r", encoding="utf-8"
    ) as f:
        behavior = json.load(f)["behavior"]

    env = load_env()
    elements = {}

    for step in behavior:
        action = step.get("action")
        log = step.get("log")
        log("step_start", f"{action} 시작")
        
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
        log("step_end", f"{action} 완료")
        if log:
            log("message", log)


def main():
    log("main", "진입")

    log("create_driver", "Chrome 드라이버 생성")
    driver = create_chrome_driver()  # ✅ 자동 드라이버 탐색
    log("create_driver", "Chrome 드라이버 생성 완료")

    log("login", "로그인 시퀀스")
    try:
        run_login(driver)
        log("login", "로그인 시퀀스 성공")
    except Exception as e:
        logger.exception(f"[{MODULE_NAME} > login] 로그인 시퀀스 실패")
        driver.quit()
        raise

    log("sales_analysis", "매출 분석")
    try:
        run_sales_analysis(driver)
        log("sales_analysis", "매출 분석 성공")
    except Exception as e:
        logger.exception(f"[{MODULE_NAME} > sales_analysis] 매출 분석 실패")
        driver.quit()
        raise

    log("module_map", "모듈 맵 저장")
    write_module_map()
    log("module_map", "모듈 맵 저장 완료")

    input("⏸ 로그인 화면 유지 중. Enter를 누르면 종료됩니다.")

    log("quit", "드라이버 종료")
    driver.quit()
    log("quit", "드라이버 종료 완료")


if __name__ == "__main__":
    main()
