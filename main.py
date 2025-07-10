from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from login.login_bgf import login_bgf


def click_login_button(driver: webdriver.Chrome) -> None:
    """Click the login button on the Nexacro login form."""

    js = """
try {
    nexacro.getApplication()
        .mainframe.HFrameSet00.LoginFrame.form.div_login.form
        .btn_login.click();
} catch (e) {
    console.error('login click error', e);
}
"""
    driver.execute_script(js)

SCRIPT_DIR = Path(__file__).with_name("scripts")


def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_experimental_option("detach", True)
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

    # 로그인 버튼 클릭만 필요한 경우를 위해 별도 호출
    click_login_button(driver)

    scripts = [
        "click_all_mid_categories.js",
        "wait_for_detail_grid.js",
        "extract_detail_data.js",
    ]
    for name in scripts:
        run_script(driver, name)

    data = wait_for_data(driver, timeout=15)
    if data:
        path = save_to_txt(data)
        print(f"saved to {path}")
    else:
        print("no data found")


if __name__ == "__main__":
    main()
