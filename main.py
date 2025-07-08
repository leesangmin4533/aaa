from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os
import time

from login.login_bgf import login_bgf
from analysis import (
    navigate_to_category_mix_ratio,
    parse_mix_ratio_data,
    click_all_product_codes,
    extract_product_info,
    export_product_data,
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

    if not navigate_to_category_mix_ratio(driver):
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
        click_all_product_codes(driver)
        time.sleep(3)
        rows = extract_product_info(driver)
        if not rows:
            print("[export][WARNING] 상품 데이터 없음")
            try:
                driver.save_screenshot("fail_product_data.png")
            except Exception as se:
                print("[export][ERROR] screenshot failed:", se)
        else:
            output_path = export_product_data(rows, "code_outputs")
            print(f"exported product data to {output_path}")
    except Exception as e:
        print("[export][ERROR] 데이터 수집 실패:", e)


if __name__ == "__main__":
    main()
