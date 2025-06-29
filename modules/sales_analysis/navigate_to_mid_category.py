from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from log_util import create_logger

MODULE_NAME = "navigate_mid"


log = create_logger(MODULE_NAME)


def navigate_to_mid_category_sales(driver):
    """Navigate to the '중분류별 매출 구성' page under sales analysis."""
    log("open_menu", "실행", "매출분석 메뉴 클릭")
    driver.find_element(By.XPATH, '//*[@id="mainframe.HFrameSet00.VFrameSet00.TopFrame.form.div_topMenu.form.STMB000_M0"]').click()
    time.sleep(1)

    log("wait_mid_menu", "실행", "중분류 메뉴 등장 대기")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="mainframe.HFrameSet00.VFrameSet00.TopFrame.form.pdiv_topMenu_STMB000_M0.form.STMB011_M0"]'))
    )
    time.sleep(0.5)

    log("click_mid_sales", "실행", "중분류별 매출 구성비 클릭")
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
    log("scan_row", "실행", f"총 행 수: {len(gridrows)}")

    for row in gridrows:
        try:
            # Nexacro uses `:text` suffix for the inner text element. Searching
            # for `cell_0_0.text` does not match this pattern, so look for any
            # div whose id includes `cell_0_0` and ends with `:text`.
            cell = row.find_element(
                By.XPATH,
                ".//div[contains(@id, 'cell_0_0') and substring(@id, string-length(@id) - 5) = ':text']",
            )
            code = cell.text.strip()
            log("scan_row", "실행", f"코드 추출값: {code}")
            if code.isdigit():
                num = int(code)
                if start <= num <= end:
                    code_map[num] = cell
        except Exception as e:
            log("scan_row", "오류", f"행에서 코드 셀 탐색 실패: {e}")
            continue

    click_success = 0
    not_found_count = 0

    for num in range(start, end + 1):
        cell = code_map.get(num)
        if cell:
            try:
                log("click_code", "실행", f"코드 {num:03d} 클릭 중...")
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable(cell)).click()
                click_success += 1
                time.sleep(1.0)
            except Exception as e:
                log("click_code", "오류", f"코드 {num:03d} 클릭 실패: {e}")
        else:
            not_found_count += 1

    total = end - start + 1
    log("click_code", "실행", f"전체 {total} 중 클릭 성공 {click_success}건, 없음 {not_found_count}건")
