from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bgf_login_project.login.login_bgf import login_bgf
from bgf_login_project.analysis import (
    go_to_category_mix_ratio,
    parse_mix_ratio_data,
    extract_code_details_with_button_scroll,
)
import os

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
        print(df.head())
    except Exception as e:
        print("analysis error", e)

    try:
        extract_code_details_with_button_scroll(driver)
    except Exception as e:
        print("code detail extraction error", e)


if __name__ == "__main__":
    main()
