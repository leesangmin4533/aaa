from selenium.webdriver.common.by import By

def navigate_sales_ratio(driver):
    """Navigate to the '매출분석 > 중분류별 매출 구성비' menu."""
    # Example navigation - adjust selectors as needed
    menu = driver.find_element(By.LINK_TEXT, '매출분석')
    menu.click()
    sub_menu = driver.find_element(By.LINK_TEXT, '중분류별 매출 구성비')
    sub_menu.click()
