from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from log_util import create_logger

MODULE_NAME = "navigation"

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
