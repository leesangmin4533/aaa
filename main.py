from selenium import webdriver
from login_runner import run_login
import json
import time


def run_sales_analysis(driver):
    """Execute sales analysis steps defined in mid_category_sales_ssv.json."""
    from ssv_listener import extract_ssv_from_cdp
    from login_runner import load_env

    with open("modules/sales_analysis/mid_category_sales_ssv.json", "r", encoding="utf-8") as f:
        behavior = json.load(f)["behavior"]

    env = load_env()
    elements = {}

    for step in behavior:
        action = step.get("action")
        log = step.get("log")

        if action == "navigate_menu":
            from modules.sales_analysis.navigate_to_mid_category import navigate_to_mid_category_sales
            navigate_to_mid_category_sales(driver)
        elif action == "click":
            driver.find_element("xpath", step["target_xpath"]).click()
        elif action == "sleep":
            # Allow pauses between actions when server responses are required
            time.sleep(step.get("seconds", 1))
        elif action == "extract_network_response":
            extract_ssv_from_cdp(driver, keyword=step["match"], save_to=step["save_to"])
        elif action == "parse_ssv":
            from parse_and_save import parse_ssv, save_filtered_rows
            with open(step["input"], "r", encoding="utf-8") as f:
                rows = parse_ssv(f.read())
            save_filtered_rows(
                rows,
                step["save_to"],
                fields=step.get("fields"),
                filter_dict=step.get("filter"),
            )

        if log:
            print(log)


def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--remote-debugging-port=9222")
    # options.add_argument("--headless=new")  # headless 환경에서 실행 가능

    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=options)  # ✅ 자동 드라이버 탐색
    run_login(driver)
    run_sales_analysis(driver)

    input("⏸ 로그인 화면 유지 중. Enter를 누르면 종료됩니다.")
    driver.quit()


if __name__ == "__main__":
    main()
