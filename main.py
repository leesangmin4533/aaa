from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os

from login.login_bgf import login_bgf
from analysis import (
    go_to_mix_ratio_screen,
    parse_mix_ratio_data,
    extract_product_info,
    click_all_product_codes,
)

def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_experimental_option("detach", True)  # 창 자동 종료 방지
    return webdriver.Chrome(service=Service(), options=options)


def main() -> None:
    print("[main] main() 진입")  # 루프 여부 추적용
    driver = create_driver()
    cred_path = os.environ.get("CREDENTIAL_FILE")
    success = login_bgf(driver, credential_path=cred_path)
    if not success:
        print("login failed")
        driver.quit()
        return

    if not go_to_mix_ratio_screen(driver):
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
        total = click_all_product_codes(driver)
        print(f"clicked {total} product codes")
    except Exception as e:
        print("auto click error", e)

    try:
        extract_product_info(driver)
    except Exception as e:
        print("product info extraction error", e)


if __name__ == "__main__":
    main()
