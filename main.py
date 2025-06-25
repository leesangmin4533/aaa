import os
import json
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By

from navigate_sales_ratio import navigate_sales_ratio


def load_login_structure():
    """Always recreate the login structure before loading it."""
    from crawl.login_structure import create_login_structure

    # Refresh the login structure on every run
    create_login_structure()

    path = os.path.join('structure', 'login_structure.json')
    with open(path) as f:
        return json.load(f)


POPUP_CLOSE_SELECTORS = [
    "//*[contains(text(), '닫기')]",
    "button.close",
    "div.popup .close",
    "[id*=close]",
    "[class*=close]"
]


def close_popups(driver, max_loops=2):
    """Close any popups that may appear after login."""
    for _ in range(max_loops):
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
        if not closed_any:
            break


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

    id_field = driver.find_element(By.CSS_SELECTOR, cfg['id_selector'])
    id_field.send_keys(login_id)

    pw_field = driver.find_element(By.CSS_SELECTOR, cfg['password_selector'])
    pw_field.send_keys(login_pw)

    submit_btn = driver.find_element(By.CSS_SELECTOR, cfg['submit_selector'])
    submit_btn.click()

    # Ensure all popups are closed before proceeding
    close_popups(driver)

    if datetime.now().weekday() == 0:
        navigate_sales_ratio(driver)
        extract_sales_data()

    # Placeholder for data extraction logic after navigation
    # Data should be saved under sales_analysis

    driver.quit()


if __name__ == '__main__':
    main()
