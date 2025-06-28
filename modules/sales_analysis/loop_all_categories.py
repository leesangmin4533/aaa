from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from modules.common.login import run_login
from modules.sales_analysis.navigate_to_mid_category import (
    navigate_to_mid_category_sales,
)
from modules.sales_analysis.process_one_category import process_one_category
from selenium.webdriver.common.by import By


def main() -> None:
    """Run automation across mid-category rows based on visible gridrows."""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--remote-debugging-port=9222")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=options)
    run_login(driver)
    navigate_to_mid_category_sales(driver)

    index = 0
    while True:
        xpath = (
            f"//*[@id='mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm.form.div2.form.gdList.body.gridrow_{index}.cell_0_0']"
        )
        try:
            driver.find_element(By.XPATH, xpath)
        except NoSuchElementException:
            print(f"⛔ gridrow_{index} 존재하지 않음 — 루프 종료")
            break

        try:
            success = process_one_category(driver, index)
            if not success:
                print(f"⚠ 중분류 {index:03d} 처리 실패 — 다음 항목으로 계속")
        except Exception as e:
            print(f"⚠ 예외 발생 (중분류 {index:03d}): {e}")
        finally:
            index += 1

    input("⏸ Press Enter to exit.")
    driver.quit()


if __name__ == "__main__":
    main()
