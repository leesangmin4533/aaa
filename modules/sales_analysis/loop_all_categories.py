from selenium import webdriver
from modules.common.login import run_login

from modules.sales_analysis.navigate_to_mid_category import navigate_to_mid_category_sales
from modules.sales_analysis.process_one_category import process_one_category


def main(start: int = 0, end: int = 900) -> None:
    """Run automation across mid-category rows."""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--remote-debugging-port=9222")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=options)
    run_login(driver)
    navigate_to_mid_category_sales(driver)

    for idx in range(start, end + 1):
        if not process_one_category(driver, idx):
            print(f"❌ 루프 중단 @ {idx:03d}")
            break

    input("⏸ Press Enter to exit.")
    driver.quit()


if __name__ == "__main__":
    main()
