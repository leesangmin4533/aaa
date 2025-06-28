from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from modules.common.login import run_login
from modules.common.driver import create_chrome_driver
from modules.sales_analysis.navigate_to_mid_category import (
    navigate_to_mid_category_sales,
)
from modules.sales_analysis.process_one_category import process_one_category
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

MODULE_NAME = "loop_all_categories"


def log(step: str, msg: str) -> None:
    print(f"\u25b6 [{MODULE_NAME} > {step}] {msg}")


def main() -> None:
    """Run automation across mid-category rows based on visible gridrows."""
    driver = create_chrome_driver()
    run_login(driver)
    navigate_to_mid_category_sales(driver)

    index = 0
    while True:
        xpath = (
            f"//*[@id='mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm.form.div2.form.gdList.body.gridrow_{index}.cell_0_0']"
        )
        log("check_row", f"{index:03d}번 row 검사 중...")
        try:
            # Wait up to 2 seconds for the row element to appear
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
        except TimeoutException:
            log("no_row", f"gridrow_{index} 존재하지 않음 또는 로딩되지 않음 — 루프 종료")
            break

        try:
            success = process_one_category(driver, index)
            if not success:
                log("row_fail", f"중분류 {index:03d} 처리 실패 — 다음 항목으로 계속")
        except Exception as e:
            log("row_error", f"예외 발생 (중분류 {index:03d}): {e}")
        finally:
            index += 1

    input("⏸ Press Enter to exit.")
    driver.quit()


if __name__ == "__main__":
    main()
