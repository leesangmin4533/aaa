from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from login.login_bgf import login_bgf
from utils.popup_util import close_popups_after_delegate
from utils.log_parser import extract_tab_lines
from utils import append_unique_lines, convert_txt_to_excel
from utils.db_util import write_sales_data
from utils.log_util import create_logger

SCRIPT_DIR = Path(__file__).with_name("scripts")
CODE_OUTPUT_DIR = Path(__file__).with_name("code_outputs")
# 자동 실행할 기본 스크립트 파일명
DEFAULT_SCRIPT = "auto_collect_mid_products.js"
LISTENER_SCRIPT = "data_collect_listener.js"
NAVIGATION_SCRIPT = "navigation.js"

# Logger used for both console and file output
log = create_logger("main")


def get_script_files() -> list[str]:
    """Return all JavaScript file names in the scripts directory sorted by name."""
    return sorted(p.name for p in SCRIPT_DIR.glob("*.js"))

# code_outputs/날짜.txt 필드 저장 순서를 지정한다.
FIELD_ORDER = [
    "midCode",
    "midName",
    "productCode",
    "productName",
    "sales",
    "order",
    "purchase",
    "discard",
    "stock",
]


def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_experimental_option("detach", True)
    caps = DesiredCapabilities.CHROME.copy()
    caps["goog:loggingPrefs"] = {"browser": "ALL"}
    for key, value in caps.items():
        options.set_capability(key, value)
    return webdriver.Chrome(service=Service(), options=options)


def run_script(driver: webdriver.Chrome, name: str) -> Any:
    path = SCRIPT_DIR / name
    if not path.exists():
        msg = f"script file not found: {path}"
        print(msg)
        log("run_script", "ERROR", msg)
        raise FileNotFoundError(msg)
    with open(path, "r", encoding="utf-8") as f:
        js = f.read()
    return driver.execute_script(js)


def wait_for_data(driver: webdriver.Chrome, timeout: int = 10):
    for _ in range(timeout * 2):
        try:
            data = driver.execute_script("return window.__parsedData__ || null")
            if data:
                return data
        except Exception:
            pass
        time.sleep(0.5)
    return None


def wait_for_mix_ratio_page(driver: webdriver.Chrome, timeout: int = 10) -> bool:
    """중분류별 매출 구성비 화면의 그리드가 나타날 때까지 대기한다."""
    js = (
        "return document.querySelector("
        "\"div[id*='gdList.body'][id*='cell_'][id$='_0:text']\""
        ") !== null;"
    )
    for _ in range(timeout * 2):
        try:
            if driver.execute_script(js):
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def save_to_txt(data: Any, output: str | Path | None = None) -> Path:
    if output is None:
        CODE_OUTPUT_DIR.mkdir(exist_ok=True)
        fname = datetime.now().strftime("%Y%m%d") + ".txt"
        output = CODE_OUTPUT_DIR / fname
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with open(output, "w", encoding="utf-8") as f:
        if isinstance(data, list):
            for row in data:
                if isinstance(row, dict):
                    # 필드 순서에 맞춰 값을 가져온 뒤 탭으로 구분하여 기록한다.
                    f.write(
                        "\t".join(str(row.get(k, "")) for k in FIELD_ORDER) + "\n"
                    )
                else:
                    text = str(row).rstrip("\n")
                    parts = text.split("\t")
                    if len(parts) >= 3:
                        for i in range(3, len(parts)):
                            if parts[i] == "":
                                parts[i] = "0"
                        text = "\t".join(parts)
                    f.write(text + "\n")
        else:
            f.write(str(data))
    return output


def main() -> None:
    driver = create_driver()
    cred_path = os.environ.get("CREDENTIAL_FILE")
    if not login_bgf(driver, credential_path=cred_path):
        print("login failed")
        log("login", "ERROR", "login failed")
        driver.quit()
        return

    # TensorFlow delegate 초기화 로그 이후 다시 팝업을 닫는다
    try:
        close_popups_after_delegate(driver)
    except Exception as e:
        print(f"delegate popup close failed: {e}")
        log("popup", "WARNING", f"delegate popup close failed: {e}")
    # 매출분석 화면으로 이동한다
    run_script(driver, NAVIGATION_SCRIPT)
    if not wait_for_mix_ratio_page(driver):
        print("page load timeout")
        log("navigation", "ERROR", "page load timeout")
        driver.quit()
        return



    # 중분류 매출 구성비 화면 진입 후 자동 수집 스크립트를 실행한다
    date_str = datetime.now().strftime("%y%m%d")
    output_path = CODE_OUTPUT_DIR / f"{date_str}.txt"
    if output_path.exists():
        output_path.unlink()

    run_script(driver, DEFAULT_SCRIPT)
    run_script(driver, LISTENER_SCRIPT)

    logs = driver.execute_script("return window.__midCategoryLogs__ || []")
    if logs:
        print("중분류 클릭 로그:", logs)
        log("mid_category", "INFO", f"logs: {logs}")

    while True:
        lines = driver.execute_script(
            "var d = window.__liveData__ || []; window.__liveData__ = []; return d;"
        )
        if lines:
            added = append_unique_lines(output_path, lines)
            print(f"appended {added} lines")
            log("collect", "INFO", f"appended {added} lines")

        parsed = driver.execute_script("return window.__parsedData__ || null")
        if parsed is not None:
            break
        time.sleep(0.5)

    db_path = CODE_OUTPUT_DIR / f"{datetime.now():%Y%m%d}.db"
    try:
        inserted = write_sales_data(parsed, db_path)
        print(f"db saved to {db_path}, inserted {inserted} rows")
        log("db", "INFO", f"db saved to {db_path}, inserted {inserted} rows")
    except Exception as e:
        print(f"db write failed: {e}")
        log("db", "ERROR", f"db write failed: {e}")

    print(f"saved to {output_path}")
    log("output", "INFO", f"saved to {output_path}")
    time.sleep(3)
    excel_dir = CODE_OUTPUT_DIR / "mid_excel"
    excel_dir.mkdir(parents=True, exist_ok=True)
    excel_path = excel_dir / f"{date_str}.xlsx"

    try:
        convert_txt_to_excel(str(output_path), str(excel_path))
        print(f"converted to {excel_path}")
        log("excel", "INFO", f"converted to {excel_path}")
    except Exception as e:
        print(f"excel conversion failed: {e}")
        log("excel", "ERROR", f"excel conversion failed: {e}")

    error = None
    try:
        error = driver.execute_script("return window.__parsedDataError__ || null")
    except Exception:
        pass
    if error:
        print("스크립트 오류:", error)
        log("script", "ERROR", f"스크립트 오류: {error}")

    try:
        logs = driver.get_log("browser")
    except Exception as e:
        print(f"get_log failed: {e}")
        log("browser_log", "ERROR", f"get_log failed: {e}")
        logs = None
    if logs:
        lines = extract_tab_lines(logs)
        if lines:
            print("추출된 로그 데이터:")
            log("browser_log", "INFO", "추출된 로그 데이터:")
            for line in lines:
                print(line)
                log("browser_log", "INFO", line)
        else:
            print("브라우저 콘솔 로그:")
            log("browser_log", "INFO", "브라우저 콘솔 로그:")
            for entry in logs:
                print(entry)
                log("browser_log", "INFO", str(entry))


if __name__ == "__main__":
    main()
