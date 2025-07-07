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
    time.sleep(2)
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
    """기존 방식: 미리 정해진 행 개수만큼 셀 클릭 후 스크롤."""
    for i in range(rows):
        if click_code_cell(driver, i):
            time.sleep(delay)
        if not click_scroll_button(driver):
            break
        time.sleep(delay)


def extract_code_details_strict_sequence(driver: WebDriver, delay: float = 1.0):
    """001 ~ 900까지 순차적으로 코드 셀을 탐색하며 클릭 후 스크롤 버튼을 누른다."""
    for num in range(1, 901):
        code_str = f"{num:03}"
        print(f"[code-check] '{code_str}' 셀 탐색 중...")

        element = driver.execute_script(
            """
return [...document.querySelectorAll("div")]
  .find(el => el.innerText?.trim() === arguments[0] && el.id?.includes("gridrow_") && el.id?.includes("cell_0_0:text"));
""",
            code_str,
        )

        if element:
            print(f"[code-click] '{code_str}' 셀 클릭")
            dispatch_mouse_event(driver, element)
            time.sleep(delay)

            if click_scroll_button(driver):
                print(f"[scroll] 스크롤 버튼 클릭 완료")
            else:
                print(f"[scroll][END] 스크롤 버튼 없음 → 종료")
                break
            time.sleep(delay)
        else:
            print(f"[code-skip] '{code_str}' 셀 없음 → 패스")


def parse_mix_ratio_data(driver: WebDriver):
    """그리드에서 코드 데이터를 추출하여 DataFrame으로 반환"""
    try:
        import pandas as pd
    except ImportError:
        print("[parse_mix_ratio_data][ERROR] pandas 로드 실패")
        return None

    script = """
return [...document.querySelectorAll("div")]
  .filter(el => el.innerText?.trim().match(/^\\d{3}$/))
  .map(el => el.innerText.trim());
"""
    try:
        rows = driver.execute_script(script)
        if not rows:
            print("[parse_mix_ratio_data][WARN] 추출된 코드 행 없음")
            return None
        print(f"[parse_mix_ratio_data][INFO] 추출된 코드 수: {len(rows)}")
        return pd.DataFrame({'code': rows})
    except Exception as e:
        print("[parse_mix_ratio_data][ERROR] 스크립트 실행 실패:", e)
        return None
