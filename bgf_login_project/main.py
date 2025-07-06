from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from login.login_bgf import login_bgf
from analysis import go_to_category_mix_ratio, parse_mix_ratio_data
import os

def create_driver():
    options = Options()
    options.add_experimental_option("detach", True)  # 창 자동 종료 방지
    return webdriver.Chrome(service=Service(), options=options)

if __name__ == "__main__":
    driver = create_driver()
    cred_path = os.environ.get("CREDENTIAL_FILE")
    success = login_bgf(driver, credential_path=cred_path)
    if success:
        go_to_category_mix_ratio(driver)
        try:
            df = parse_mix_ratio_data(driver)
            print(df.head())
        except Exception as e:
            print("analysis error", e)
    else:
        print("login failed")
