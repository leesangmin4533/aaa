import os
import json
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
import traceback

from navigate_sales_ratio import navigate_sales_ratio


def load_login_structure():
    """Load login structure file or create it using the crawler."""
    path = os.path.join('structure', 'login_structure.json')
    if not os.path.exists(path):
        from crawl.login_structure import create_login_structure
        create_login_structure()
    with open(path) as f:
        return json.load(f)


POPUP_CLOSE_SELECTORS = [
    "//*[contains(text(), '닫기')]",
    "//*[normalize-space()='닫기']",
    "button.close",
    "div.popup .close",
    "[id*=close]",
    "[class*=close]"
]


def close_popups(driver, min_loops=2, max_loops=5):
    """Close any popups that may appear after login."""
    loops = 0
    while loops < max_loops:
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
        loops += 1
        if not closed_any and loops >= min_loops:
            break


def extract_sales_data():
    """Placeholder for future data extraction logic."""
    os.makedirs('sales_analysis', exist_ok=True)
    with open(os.path.join('sales_analysis', 'data.txt'), 'w') as f:
        f.write('placeholder')


def save_error_logs(driver, exc):
    """Save screenshot, DOM and log message when an error occurs."""
    os.makedirs('logs', exist_ok=True)
    driver.save_screenshot(os.path.join('logs', 'error.png'))
    with open(os.path.join('logs', 'error_dom.html'), 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    with open(os.path.join('logs', 'error.log'), 'w', encoding='utf-8') as f:
        f.write(
            '자동화 수행 중 오류 발생. 스크린샷 및 DOM 저장됨.\n' +
            ''.join(traceback.format_exception_only(type(exc), exc))
        )


def main():
    load_dotenv()
    login_id = os.getenv('LOGIN_ID')
    login_pw = os.getenv('LOGIN_PW')
    if not login_id or not login_pw:
        raise ValueError('LOGIN_ID or LOGIN_PW not set in environment')

    cfg = load_login_structure()

    driver = webdriver.Chrome()
    try:
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

    except Exception as exc:
        save_error_logs(driver, exc)
        raise
    finally:
        driver.quit()


if __name__ == '__main__':
    main()
