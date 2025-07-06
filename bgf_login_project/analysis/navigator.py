from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

from .selector import SELECTORS


def go_to_category_mix_ratio(driver):
    """매출분석 > 중분류별 매출 구성비 화면으로 이동한다."""
    wait = WebDriverWait(driver, 10)

    sales_menu = wait.until(
        EC.element_to_be_clickable((By.XPATH, SELECTORS["sales_analysis_menu_xpath"]))
    )
    sales_menu.click()
    time.sleep(0.5)

    ratio_menu = wait.until(
        EC.element_to_be_clickable((By.XPATH, SELECTORS["category_mix_ratio_menu_xpath"]))
    )
    ratio_menu.click()
    time.sleep(1)
