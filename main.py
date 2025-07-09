from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import os


from login.login_bgf import login_bgf
from analysis import (
    navigate_to_category_mix_ratio,
    parse_mix_ratio_data,
    click_all_product_codes,
    export_product_data,
)

def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_experimental_option("detach", True)  # 창 자동 종료 방지
    return webdriver.Chrome(service=Service(), options=options)


def wait_for_exported_rows(driver: webdriver.Chrome, timeout: int = 10):
    """Poll window.__exportedRows until data is available."""
    import time

    for _ in range(timeout * 2):
        try:
            rows = driver.execute_script("return window.__exportedRows || []")
            if rows and isinstance(rows, list) and len(rows) > 0:
                return rows
        except Exception:
            pass
        time.sleep(0.5)
    return []


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
        print("[JS] 자동 클릭 실행됨")

        rows = wait_for_exported_rows(driver, timeout=15)
        print(f"[DEBUG] 수집된 행 수: {len(rows)}")
        if not rows:
            print("[export][WARNING] 수집된 데이터 없음")
            driver.save_screenshot("fail_product_data.png")
        else:
            output_path = export_product_data(rows, "code_outputs")
            print(f"[SUCCESS] 저장 완료 → {output_path}")
    except Exception as e:
        print("[export][ERROR] 예외 발생:", e)


if __name__ == "__main__":
    main()
