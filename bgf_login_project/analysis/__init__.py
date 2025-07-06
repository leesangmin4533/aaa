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
    """주어진 텍스트를 가진 ``div`` 요소를 찾아 클릭한다."""
    end = time.time() + timeout
    while time.time() < end:
        element = driver.execute_script(
            "return [...document.querySelectorAll('div')].find(el => el.innerText?.trim() === arguments[0])",
            text,
        )
        if element:
            print(f"[click_menu_by_text] '{text}' 요소 찾음 → 클릭 시도")
            dispatch_mouse_event(driver, element)
            return True
        time.sleep(0.5)
    print(f"[click_menu_by_text][WARN] '{text}' 요소 탐색 실패")
    return False


def go_to_category_mix_ratio(driver: WebDriver) -> bool:
    """Navigate to the category mix ratio screen with detailed logging."""
    print("[navigation] '매출분석' 클릭 시도 중...")
    if not click_menu_by_text(driver, '매출분석', timeout=10):
        print("[navigation][ERROR] '매출분석' 클릭 실패: 요소 탐색 실패 또는 클릭 불가")
        driver.save_screenshot('fail_매출분석.png')
        return False

    print("[navigation] '매출분석' 클릭 성공 → 화면 로딩 대기")
    time.sleep(3)

    print("[navigation] '중분류별 매출 구성비' 클릭 시도 중...")
    if not click_menu_by_text(driver, '중분류별 매출 구성비', timeout=10):
        print("[navigation][ERROR] '중분류별 매출 구성비' 클릭 실패: 요소 탐색 실패 또는 클릭 불가")
        driver.save_screenshot('fail_중분류별매출구성비.png')
        return False

    print("[navigation] '중분류별 매출 구성비' 클릭 성공")
    return True


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
