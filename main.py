import os
import json
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from navigate_sales_ratio import navigate_sales_ratio


def load_login_structure():
    """Recreate and load the XPath-based login structure."""
    from crawl.login_structure_xpath import create_login_structure_xpath

    # Refresh the login structure on every run. If any required login element
    # cannot be found an exception is raised and the program aborts.
    create_login_structure_xpath(fail_on_missing=True)

    xpath_path = os.path.join('structure', 'login_structure_xpath.json')
    with open(xpath_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    return cfg


POPUP_CLOSE_SELECTORS = [
    "//*[contains(text(), '닫기')]",
    "button.close",
    "div.popup .close",
    "[id*=close]",
    "[class*=close]"
]


def close_popups(driver, min_loops: int = 2, max_loops: int = 5) -> bool:
    """Close any popups that may appear after login.

    The function runs at least ``min_loops`` iterations to catch popups that
    might appear after the first one is closed. It stops early only after
    ``min_loops`` attempts when no additional popups are detected.
    """
    for i in range(max_loops):
        closed_any = False
        for selector in POPUP_CLOSE_SELECTORS:
            try:
                if selector.startswith('//'):
                    buttons = driver.find_elements(By.XPATH, selector)
                else:
                    buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in buttons:
                    try:
                        btn.click()
                        closed_any = True
                    except Exception:
                        pass
            except Exception:
                pass
        if not closed_any and i >= (min_loops - 1):
            break

    # Verify no close buttons remain
    for selector in POPUP_CLOSE_SELECTORS:
        try:
            if selector.startswith('//'):
                if driver.find_elements(By.XPATH, selector):
                    return False
            else:
                if driver.find_elements(By.CSS_SELECTOR, selector):
                    return False
        except Exception:
            pass

    return True


def extract_sales_data():
    """Placeholder for future data extraction logic."""
    os.makedirs('sales_analysis', exist_ok=True)
    with open(os.path.join('sales_analysis', 'data.txt'), 'w') as f:
        f.write('placeholder')


def main():
    load_dotenv()
    login_id = os.getenv('LOGIN_ID')
    login_pw = os.getenv('LOGIN_PW')
    if not login_id or not login_pw:
        raise ValueError('LOGIN_ID or LOGIN_PW not set in environment')

    cfg = load_login_structure()

    driver = webdriver.Chrome()
    driver.get(cfg['url'])

    # Use XPath selectors for interaction while keeping CSS selectors available
    # for compatibility with future changes to the page structure.
    WebDriverWait(driver, 20).until(
        lambda d: len(d.find_elements(By.CLASS_NAME, "nexainput")) >= 2
    )
    inputs = driver.find_elements(By.CLASS_NAME, "nexainput")
    driver.execute_script(
        "arguments[0].value = arguments[1];",
        inputs[0],
        login_id,
    )
    driver.execute_script(
        "arguments[0].value = arguments[1];",
        inputs[1],
        login_pw,
    )

    submit_btn = driver.find_element(By.XPATH, cfg['submit_xpath'])
    try:
        submit_btn.click()
    except Exception:
        pass

    # Ensure all popups are closed before proceeding
    popups_closed = close_popups(driver)

    if popups_closed and datetime.now().weekday() == 0:
        navigate_sales_ratio(driver)
        extract_sales_data()

    # Placeholder for data extraction logic after navigation
    # Data should be saved under sales_analysis

    driver.quit()


if __name__ == '__main__':
    main()
