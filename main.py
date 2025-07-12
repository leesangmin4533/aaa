from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from login.login_bgf import login_bgf
from utils.popup_util import close_popups_after_delegate
from analysis import navigate_to_category_mix_ratio

SCRIPT_DIR = Path(__file__).with_name("scripts")


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


def save_to_txt(data: Any, output: str | Path = "output.txt") -> Path:
    output = Path(output)
    with open(output, "w", encoding="utf-8") as f:
        if isinstance(data, list):
            for row in data:
                if isinstance(row, dict):
                    f.write("\t".join(str(v) for v in row.values()) + "\n")
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



    # 중분류 클릭 후 로그를 수집한다
    run_script(driver, "click_all_mid_categories.js")
    logs = driver.execute_script("return window.__midCategoryLogs__ || []")
    print("중분류 클릭 로그:", logs)

    # 우측 그리드가 준비됐는지 확인한다
    run_script(driver, "wait_for_detail_grid.js")
    print("grid ready:", driver.execute_script("return window.__gridReady"))

    # 최종 데이터를 추출한다
    run_script(driver, "extract_detail_data.js")

    data = wait_for_data(driver, timeout=15)
    if data:
        path = save_to_txt(data)
        print(f"saved to {path}")
    else:
        print("no data found")


if __name__ == "__main__":
    main()
