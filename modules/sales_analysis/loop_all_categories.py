from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from modules.common.login import run_login
from modules.sales_analysis.navigate_to_mid_category import (
    navigate_to_mid_category_sales,
)
from modules.sales_analysis.process_one_category import process_one_category
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


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
            f"//*[@id='mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.WorkFrame.form.grd_msg.body.gridrow_{index}.cell_{index}_0']"
        )
        print(f"🔍 {index:03d}번 row 검사 중...")
        try:
            # Wait up to 2 seconds for the row element to appear
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
        except TimeoutException:
            print(f"⛔ gridrow_{index} 존재하지 않음 또는 로딩되지 않음 — 루프 종료")
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
