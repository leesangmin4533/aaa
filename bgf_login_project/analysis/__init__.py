import time
from selenium.webdriver.remote.webdriver import WebDriver


def dispatch_mouse_event(driver: WebDriver, element):
    driver.execute_script(
        """
var rect = arguments[0].getBoundingClientRect();
['mousedown', 'mouseup', 'click'].forEach(type => {
    arguments[0].dispatchEvent(new MouseEvent(type, {
        bubbles: true,
        cancelable: true,
        view: window,
        clientX: rect.left + rect.width / 2,
        clientY: rect.top + rect.height / 2
    }));
});
""",
        element,
    )


def click_menu_by_text(driver: WebDriver, text: str, timeout: int = 5) -> bool:
    """class가 nexatextitem이고 텍스트가 일치하는 요소를 클릭"""
    end = time.time() + timeout
    while time.time() < end:
        element = driver.execute_script(
            "return [...document.querySelectorAll('div.nexatextitem')]\n            .find(el => el.innerText.trim() === arguments[0])",
            text,
        )
        if element:
            dispatch_mouse_event(driver, element)
            return True
        time.sleep(0.5)
    return False


def go_to_category_mix_ratio(driver: WebDriver) -> None:
    click_menu_by_text(driver, "매출분석")
    time.sleep(1)
    click_menu_by_text(driver, "중분류별 매출 구성비")
    time.sleep(1)


def click_code_cell(driver: WebDriver, index: int) -> bool:
    selector = f"div[id*='gridrow_{index}'][id*='.cell_0_0:text']"
    element = driver.execute_script(
        "return document.querySelector(arguments[0])",
        selector,
    )
    if element:
        dispatch_mouse_event(driver, element)
        return True
    return False


def click_scroll_button(driver: WebDriver) -> bool:
    js = """
return document.querySelector('div.ButtonControl.incbutton') ||
       [...document.querySelectorAll('div')].find(el => el.id?.endsWith('incbutton:icontext'));
"""
    element = driver.execute_script(js)
    if element:
        dispatch_mouse_event(driver, element)
        return True
    return False


def extract_code_details_with_button_scroll(driver: WebDriver, rows: int = 10, delay: float = 1.0) -> None:
    for i in range(rows):
        if click_code_cell(driver, i):
            time.sleep(delay)
        if not click_scroll_button(driver):
            break
        time.sleep(delay)


def parse_mix_ratio_data(driver: WebDriver):
    """그리드에서 데이터 프레임을 생성하는 기본 구조."""
    try:
        import pandas as pd
    except Exception:
        return None
    script = (
        "return [...document.querySelectorAll(\"[id^='gridrow_'][id*='cell_0_0:text']\")]."
        "map(el => el.innerText)"
    )
    rows = driver.execute_script(script)
    return pd.DataFrame({'code': rows}) if rows else None
