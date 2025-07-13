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
from analysis import navigate_to_category_mix_ratio

SCRIPT_DIR = Path(__file__).with_name("scripts")
CODE_OUTPUT_DIR = Path(__file__).with_name("code_outputs")

# output.txt 필드 저장 순서를 지정한다.
FIELD_ORDER = [
    "midCode",
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


def save_to_txt(data: Any, output: str | Path | None = None) -> Path:
    if output is None:
        CODE_OUTPUT_DIR.mkdir(exist_ok=True)
        fname = datetime.now().strftime("%Y%m%d") + ".txt"
        output = CODE_OUTPUT_DIR / fname
    output = Path(output)
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
                    f.write(str(row) + "\n")
        else:
            f.write(str(data))
    return output


def main() -> None:
    driver = create_driver()
    cred_path = os.environ.get("CREDENTIAL_FILE")
    if not login_bgf(driver, credential_path=cred_path):
        print("login failed")
        driver.quit()
        return

    # TensorFlow delegate 초기화 로그 이후 다시 팝업을 닫는다
    try:
        close_popups_after_delegate(driver)
    except Exception as e:
        print(f"delegate popup close failed: {e}")
    # 매출분석 화면으로 이동한다
    if not navigate_to_category_mix_ratio(driver):
        print("navigation failed")
        driver.quit()
        return



    # 중분류별 클릭과 데이터 추출을 한 번에 수행한다
    # 새로운 스크롤 전체 탐색 로직을 담은 스크립트를 실행한다
    run_script(driver, "click_and_extract_full.js")
    logs = driver.execute_script("return window.__midCategoryLogs__ || []")
    scroll_logs = driver.execute_script("return window.__scrollLogs__ || []")
    print("중분류 클릭 로그:", logs)
    print("스크롤 클릭 로그:", scroll_logs)

    data = wait_for_data(driver, timeout=15)
    if data:
        path = save_to_txt(data)
        print(f"saved to {path}")
    else:
        print("no data found")


if __name__ == "__main__":
    main()
