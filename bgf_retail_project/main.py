from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bgf_retail_project.login.login_bgf import login_bgf
from bgf_retail_project.analysis import (
    go_to_category_mix_ratio,
    parse_mix_ratio_data,
    extract_code_details_strict_sequence,
)

def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_experimental_option("detach", True)  # 창 자동 종료 방지
    return webdriver.Chrome(service=Service(), options=options)


def main() -> None:
    driver = create_driver()
    cred_path = os.environ.get("CREDENTIAL_FILE")
    success = login_bgf(driver, credential_path=cred_path)
    if not success:
        print("login failed")
        driver.quit()
        return

    if not go_to_category_mix_ratio(driver):
        print("navigation failed")
        driver.quit()
        return

    try:
        df = parse_mix_ratio_data(driver)
        if df is None:
            print("[analysis][ERROR] 그리드에서 코드 데이터를 가져올 수 없음")
            driver.save_screenshot("fail_parse_mix_ratio.png")
        else:
            print(df.head())
    except Exception as e:
        print("analysis error", e)

    try:
        extract_code_details_strict_sequence(driver)
    except Exception as e:
        print("code detail extraction error", e)


if __name__ == "__main__":
    main()
