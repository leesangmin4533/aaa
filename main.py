from selenium import webdriver
from login_runner import run_login, run_step, load_env
import json


def run_sales_analysis(driver):
    with open("modules/sales_analysis/mid_category_sales.json", "r", encoding="utf-8") as f:
        steps = json.load(f)["steps"]
    env = load_env()
    elements = {}
    for step in steps:
        try:
            run_step(driver, step, elements, env)
        except Exception as e:
            print(f"\u274c Sales analysis step failed: {step.get('action')} \u2192 {e}")
            break


def main():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new")  # 브라우저 안 뜨는 원인 → 제거
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    run_login(driver)
    run_sales_analysis(driver)

    input("⏸ 로그인 화면 유지 중. Enter를 누르면 종료됩니다.")
    driver.quit()


if __name__ == "__main__":
    main()
