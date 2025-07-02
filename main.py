from modules.common.login import run_login
from modules.common.driver import create_chrome_driver
from modules.common.module_map import write_module_map
from log_util import create_logger
from popup_utils import close_popups
from modules.sales_analysis.arrow_fallback_scroll import (
    scroll_with_arrow_fallback_loop,
    navigate_to_mid_category_sales,
)
import importlib
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


def run_sales_analysis(driver, config_path=None):
    """Execute sales analysis steps defined in a JSON config, supporting loops."""
    from modules.common.network import extract_ssv_from_cdp
    from modules.common.login import load_env
    from modules.sales_analysis.mid_category_clicker import (
        click_codes_by_arrow,
        click_codes_by_loop,
        scroll_loop_click,
        grid_scroll_click_loop,
    )
    from modules.data_parser.parse_and_save import parse_ssv, save_filtered_rows

    def substitute(value: str, variables: dict) -> str:
        for k, v in variables.items():
            value = value.replace(f"${{{k}}}", str(v))
        return value

    def execute_step(step: dict, variables: dict) -> None:
        action = step.get("action")
        step_log = step.get("log")
        log("step_start", "진입", f"{action} 시작")

        if action == "click":
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
        elif action == "javascript_keydown":
            target_id = substitute(step["target_id"], variables)
            key = step.get("key", "ArrowDown")
            key_code = step.get("keyCode", 40)
            driver.execute_script(
                """
var e = new KeyboardEvent('keydown', {
    bubbles: true,
    cancelable: true,
    key: arguments[1],
    code: arguments[1],
    keyCode: arguments[2],
    which: arguments[2]
});
document.getElementById(arguments[0]).dispatchEvent(e);
""",
                target_id,
                key,
                key_code,
            )
        elif action == "cdp_keydown":
            key = step.get("key", "ArrowDown")
            vk = step.get("windowsVirtualKeyCode", 40)
            driver.execute_cdp_cmd(
                "Input.dispatchKeyEvent",
                {
                    "type": "keyDown",
                    "key": key,
                    "code": key,
                    "windowsVirtualKeyCode": vk,
                    "nativeVirtualKeyCode": vk,
                },
            )
            time.sleep(0.1)
            driver.execute_cdp_cmd(
                "Input.dispatchKeyEvent",
                {
                    "type": "keyUp",
                    "key": key,
                    "code": key,
                    "windowsVirtualKeyCode": vk,
                    "nativeVirtualKeyCode": vk,
                },
            )
        elif action == "click_codes_by_arrow":
            click_codes_by_arrow(driver)
        elif action == "gridrow_loop_click":
            max_rows = step.get("max_rows", 50)
            click_codes_by_loop(driver, row_limit=max_rows)
        elif action == "gridrow_scroll_loop_click":
            start_idx = step.get("start_index", 0)
            max_attempts = step.get("max_attempts", 100)
            do_scroll = step.get("scroll", True)
            scroll_loop_click(
                driver,
                start_index=start_idx,
                max_attempts=max_attempts,
                scroll=do_scroll,
            )
        elif action == "grid_scroll_click_loop":
            prefix = step.get("grid_id_prefix")
            suffix = step.get("cell_suffix", "")
            max_rows = step.get("max_rows", 100)
            do_scroll = step.get("scroll_into_view", True)
            enable_log = step.get("log", True)
            grid_scroll_click_loop(
                driver,
                prefix,
                suffix,
                max_rows=max_rows,
                scroll_into_view=do_scroll,
                log_enabled=enable_log,
            )
        elif action == "run_function":
            module_name = step.get("module")
            func_name = step["function"]
            if module_name:
                mod = importlib.import_module(f"modules.sales_analysis.{module_name}")
            else:
                mod = importlib.import_module("modules.sales_analysis")
            func = getattr(mod, func_name)
            args = [substitute(str(a), variables) if isinstance(a, str) else a for a in step.get("args", [])]
            kwargs = {
                k: substitute(str(v), variables) if isinstance(v, str) else v
                for k, v in step.get("kwargs", {}).items()
            }
            func(driver, *args, **kwargs)
        log("step_end", "완료", f"{action} 완료")
        if step_log:
            log("message", "실행", step_log)

    log("run_sales_analysis", "진입")
    if not config_path:
        log("run_sales_analysis", "경고", "config_path 미제공 → 실행 건너뜀")
        return

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

    log("create_driver", "실행", "Chrome 드라이버 생성")
    driver = create_chrome_driver()  # ✅ 자동 드라이버 탐색
    log("create_driver", "완료", "Chrome 드라이버 생성 완료")

    log("login", "실행", "로그인 시퀀스")
    try:
        run_login(driver)
        log("login", "완료", "로그인 시퀀스 성공")

        # ✨ 두 번째 팝업이 뜰 시간 확보
        time.sleep(1.2)

        # ✅ 팝업 자동 닫기
        try:
            popup_result = close_popups(driver)
            log(
                "popup_debug",
                "실행",
                "팝업 디버그 정보: "
                + json.dumps(
                    popup_result.get("debug", []), indent=2, ensure_ascii=False
                ),
            )
            if popup_result.get("detected"):
                log("popup_detected", "실행", "팝업 감지됨")
                if popup_result.get("closed"):
                    log("popup_closed", "완료", f"팝업 닫힘: {popup_result.get('target')}")
                else:
                    log("popup_failed", "오류", f"팝업 닫기 실패: {popup_result.get('reason')}")
                    input("수동 확인 후 Enter...")
        except Exception as e:
            logger.warning("팝업 닫기 중 예외 발생", exc_info=e)

        # ✅ 매출 분석 메뉴 진입
        navigate_to_mid_category_sales(driver)
    except Exception:
        logger.exception(f"[{MODULE_NAME} > login] 로그인 시퀀스 실패")
        driver.quit()
        return

    log("sales_analysis", "실행", "매출 분석")
    try:
        run_sales_analysis(driver)
        log("sales_analysis", "완료", "매출 분석 성공")

        log("arrow_scroll", "실행", "방향키 스크롤 루프 실행")
        scroll_with_arrow_fallback_loop(driver, max_steps=100, log_path="grid_click_log.txt")
        log("arrow_scroll", "완료", "방향키 스크롤 루프 완료")
    except Exception as e:
        logger.exception(f"[{MODULE_NAME} > sales_analysis] 매출 분석 실패")
        driver.quit()
        raise

    log("module_map", "실행", "모듈 맵 저장")
    write_module_map()
    log("module_map", "완료", "모듈 맵 저장 완료")

    input("⏸ 로그인 화면 유지 중. Enter를 누르면 종료됩니다.")

    log("quit", "실행", "드라이버 종료")
    driver.quit()
    log("quit", "완료", "드라이버 종료 완료")


if __name__ == "__main__":
    main()
