from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

MODULE_NAME = "navigate_mid"


def log(step: str, msg: str) -> None:
    print(f"\u25b6 [{MODULE_NAME} > {step}] {msg}")


def navigate_to_mid_category_sales(driver):
    """Navigate to the '중분류별 매출 구성' page under sales analysis."""
    log("open_menu", "매출분석 메뉴 클릭")
    driver.find_element(By.XPATH, '//*[@id="mainframe.HFrameSet00.VFrameSet00.TopFrame.form.div_topMenu.form.STMB000_M0"]').click()
    time.sleep(1)

    log("wait_mid_menu", "중분류 메뉴 등장 대기")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="mainframe.HFrameSet00.VFrameSet00.TopFrame.form.pdiv_topMenu_STMB000_M0.form.STMB011_M0"]'))
    )
    time.sleep(0.5)

    log("click_mid_sales", "중분류별 매출 구성비 클릭")
    driver.find_element(By.XPATH, '//*[@id="mainframe.HFrameSet00.VFrameSet00.TopFrame.form.pdiv_topMenu_STMB000_M0.form.STMB011_M0"]').click()
    time.sleep(2)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.WorkFrame.form.grd_msg.body.gridrow_0.cell_0_0"]'))
    )


def click_codes_in_order(driver, start: int = 1, end: int = 900) -> None:
    """Click mid-category grid rows in numerical order from ``start`` to ``end``.

    Parameters
    ----------
    driver:
        Selenium WebDriver instance currently on the mid-category sales page.
    start:
        Starting code number to attempt clicking. Defaults to ``1``.
    end:
        Ending code number to attempt clicking. Defaults to ``900``.
    """

    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By

    code_map = {}
    gridrows = driver.find_elements(By.XPATH, "//div[contains(@id, 'grdList.body.gridrow')]")

    for row in gridrows:
        try:
            cell = row.find_element(By.XPATH, ".//div[contains(@id, 'cell_0_0.text')]")
            code = cell.text.strip()
            if code.isdigit():
                num = int(code)
                if start <= num <= end:
                    code_map[num] = cell
        except Exception as e:
            print(f"[스킵] 행에서 코드 셀 탐색 실패: {e}")
            continue

    for num in range(start, end + 1):
        cell = code_map.get(num)
        if cell:
            try:
                print(f"▶ 코드 {num:03d} 클릭 중...")
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable(cell)).click()
                time.sleep(1.0)
            except Exception as e:
                print(f"[오류] 코드 {num:03d} 클릭 실패: {e}")
        else:
            print(f"[건너뜀] 코드 {num:03d} 없음")
