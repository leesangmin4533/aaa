from modules.common.login import run_login
from modules.common.driver import create_chrome_driver
from modules.common.module_map import write_module_map
from log_util import create_logger
from popup_utils import close_popups
import json
import time
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

MODULE_NAME = "main"


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
log = create_logger(MODULE_NAME)


def run_sales_analysis(driver, config_path="modules/sales_analysis/gridrow_click_loop.json"):
    """Execute sales analysis steps defined in a JSON config, supporting loops."""
    from modules.common.network import extract_ssv_from_cdp
    from modules.common.login import load_env
    from modules.sales_analysis.navigate_to_mid_category import navigate_to_mid_category_sales
    from modules.data_parser.parse_and_save import parse_ssv, save_filtered_rows

    def substitute(value: str, variables: dict) -> str:
        for k, v in variables.items():
            value = value.replace(f"${{{k}}}", str(v))
        return value

    def execute_step(step: dict, variables: dict) -> None:
        action = step.get("action")
        step_log = step.get("log")
        log("step_start", f"{action} 시작")

        if action == "navigate_menu":
            navigate_to_mid_category_sales(driver)
        elif action == "click":
            driver.find_element(By.XPATH, substitute(step["target_xpath"], variables)).click()
        elif action == "wait":
            xpath = substitute(step["target_xpath"], variables)
            if step.get("condition") == "presence":
                WebDriverWait(driver, step.get("timeout", 10)).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
        elif action == "sleep":
            time.sleep(step.get("seconds", 1))
        elif action == "extract_network_response":
            extract_ssv_from_cdp(
                driver,
                keyword=step["match"],
                save_to=substitute(step["save_to"], variables),
            )
        elif action == "parse_ssv":
            with open(substitute(step["input"], variables), "r", encoding="utf-8") as f:
                rows = parse_ssv(f.read())
            save_filtered_rows(
                rows,
                substitute(step["save_to"], variables),
                fields=step.get("fields"),
                filter_dict=step.get("filter"),
            )
        log("step_end", f"{action} 완료")
        if step_log:
            log("message", step_log)

    log("run_sales_analysis", "진입")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    env = load_env()
    variables = {}

    for step in config.get("behavior", []):
        execute_step(step, variables)

    if "loop" in config:
        loop = config["loop"]
        index_var = loop.get("index_var", "i")
        i = loop.get("start", 0)
        while True:
            variables[index_var] = i
            for step in loop["steps"]:
                execute_step(step, variables)
            i += 1
            variables[index_var] = i
            check_xpath = substitute(loop["until_missing_xpath"], variables)
            try:
                driver.find_element(By.XPATH, check_xpath)
            except Exception:
                break


def main():
    log("main", "진입")

    log("create_driver", "Chrome 드라이버 생성")
    driver = create_chrome_driver()  # ✅ 자동 드라이버 탐색
    log("create_driver", "Chrome 드라이버 생성 완료")

    log("login", "로그인 시퀀스")
    try:
        run_login(driver)
        log("login", "로그인 시퀀스 성공")

        # ✨ 두 번째 팝업이 뜰 시간 확보
        time.sleep(1.2)

        # ✅ 팝업 자동 닫기
        try:
            popup_result = close_popups(driver)
            print(
                "팝업 디버그 정보:",
                json.dumps(popup_result.get("debug", []), indent=2, ensure_ascii=False),
            )
            if popup_result.get("detected"):
                log("popup_detected", "팝업 감지됨")
                if popup_result.get("closed"):
                    log("popup_closed", f"팝업 닫힘: {popup_result.get('target')}")
                else:
                    log("popup_failed", f"팝업 닫기 실패: {popup_result.get('reason')}")
                    input("수동 확인 후 Enter...")
        except Exception as e:
            logger.warning("팝업 닫기 중 예외 발생", exc_info=e)
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
