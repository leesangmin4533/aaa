"""분석 및 화면 자동화를 위한 유틸리티 모듈.

코드 셀 구조
--------------
각 코드 셀은 ``div.cell_X_Y``(클릭 대상)과 ``div.cell_X_Y:text``(텍스트 표시)로
구성된다. 텍스트 추출은 ``:text`` 요소에서 수행하고, 실제 클릭 이벤트는
부모 ``div.cell_X_Y``에 전달해야 한다.
"""

import time
from pathlib import Path
from selenium.webdriver.remote.webdriver import WebDriver

from utils.log_util import create_logger
from . import grid_utils

log = create_logger("analysis")


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
            log("click_menu_by_text", "INFO", f"'{text}' 요소 찾음 → 클릭 시도")
            dispatch_mouse_event(driver, element)
            return True
        time.sleep(0.5)
    log("click_menu_by_text", "WARNING", f"'{text}' 요소 탐색 실패")
    return False


def go_to_category_mix_ratio(driver: WebDriver) -> bool:
    """Navigate to the category mix ratio screen with detailed logging."""
    log("navigation", "INFO", "'매출분석' 클릭 시도 중...")
    if not click_menu_by_text(driver, '매출분석', timeout=10):
        log("navigation", "ERROR", "'매출분석' 클릭 실패: 요소 탐색 실패 또는 클릭 불가")
        driver.save_screenshot('fail_매출분석.png')
        return False

    log("navigation", "INFO", "'매출분석' 클릭 성공 → 화면 로딩 대기")
    time.sleep(3)

    log("navigation", "INFO", "'중분류별 매출 구성비' 클릭 시도 중...")
    if not click_menu_by_text(driver, '중분류별 매출 구성비', timeout=10):
        log("navigation", "ERROR", "'중분류별 매출 구성비' 클릭 실패: 요소 탐색 실패 또는 클릭 불가")
        driver.save_screenshot('fail_중분류별매출구성비.png')
        return False

    log("navigation", "INFO", "'중분류별 매출 구성비' 클릭 성공")
    time.sleep(2)
    return True


def click_code_cell(driver: WebDriver, index: int) -> bool:
    """지정한 행 번호의 코드 셀(div.cell_X_Y)을 클릭한다.

    좌측 코드 그리드 ``gdList`` 의 행 구조는 ``gridrow_{n}.cell_{n}_0`` 형태이다.
    ``index`` 값에 해당하는 셀을 찾아 마우스 이벤트를 전달한다.
    """
    element = driver.execute_script(
        """
return [...document.querySelectorAll("div")]
  .find(el => el.id?.includes(`gridrow_${arguments[0]}`) &&
               el.id?.includes(`cell_${arguments[0]}_0`) && !el.id?.includes(":text"));
""",
        index,
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


def wait_for_detail_grid(driver: WebDriver, timeout: float = 5.0) -> bool:
    """오른쪽 상품 그리드가 로딩될 때까지 대기한다."""
    end = time.time() + timeout
    while time.time() < end:
        ready = driver.execute_script(
            """
return [...document.querySelectorAll('div')]
  .some(el => el.id?.includes('gridrow_0') && el.id?.includes('cell_0_0:text'));
"""
        )
        if ready:
            return True
        time.sleep(0.5)
    return False


def wait_for_detail_grid_value_change(
    driver: WebDriver, prev_text: str = "", timeout: float = 6.0
) -> bool:
    """gridrow_0 의 첫 셀 값이 변경될 때까지 대기한다."""
    return grid_utils.wait_for_grid_update(driver, prev_text, timeout=timeout)


def get_visible_rows(driver: WebDriver):
    """Return the fixed row index for ``gdDetail``.

    ``gdDetail`` always contains a single row (index ``0``), so this function
    simply returns ``[0]``. It remains callable for compatibility with existing
    code that expects a list of row indices.
    """

    return [0]


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
        log("code-check", "INFO", f"'{code_str}' 셀 탐색 중...")

        element = driver.execute_script(
            """
return [...document.querySelectorAll("div")]
  .find(el => el.innerText?.trim() === arguments[0] &&
              el.id?.includes("cell_") && !el.id?.includes(":text"));
""",
            code_str,
        )

        if element:
            log("code-click", "INFO", f"'{code_str}' 셀 클릭")
            dispatch_mouse_event(driver, element)
            time.sleep(delay)

            if click_scroll_button(driver):
                log("scroll", "INFO", "스크롤 버튼 클릭 완료")
            else:
                log("scroll", "INFO", "스크롤 버튼 없음 → 종료")
                break
            time.sleep(delay)
        else:
            log("code-skip", "INFO", f"'{code_str}' 셀 없음 → 패스")


def parse_mix_ratio_data(driver: WebDriver):
    """그리드에서 코드 데이터를 추출하여 DataFrame으로 반환"""
    try:
        import pandas as pd
    except ImportError:
        log("parse_mix_ratio_data", "ERROR", "pandas 로드 실패")
        return None

    script = """
return [...document.querySelectorAll("div")]
  .filter(el => el.id?.includes("cell_") && el.id?.includes(":text") &&
                 /^\\d{3}$/.test(el.innerText?.trim()))
  .map(el => el.innerText.trim());
"""
    try:
        rows = driver.execute_script(script)
        if not rows:
            log("parse_mix_ratio_data", "WARNING", "추출된 코드 행 없음")
            return None
        log("parse_mix_ratio_data", "INFO", f"추출된 코드 수: {len(rows)}")
        return pd.DataFrame({'code': rows})
    except Exception as e:
        log("parse_mix_ratio_data", "ERROR", f"스크립트 실행 실패: {e}")
        return None


def extract_product_info(
    driver: WebDriver, output_file: str | None = None, delay: float = 1.0
) -> None:
    """중분류 코드별 상품 정보를 추출하여 텍스트 파일에 저장한다.

    이 함수는 코드 셀 클릭부터 상품 행 순회까지 한 번의 루프에서 처리한다.
    매출 구성비 화면에서 왼쪽 코드(gdList)를 순차적으로 클릭한 뒤,
    오른쪽 상품 그리드(gdDetail)의 모든 행을 클릭하며 상품 정보를
    수집한다. 각 상품 행에서 ``cell_0_0:text`` 부터 ``cell_0_6:text`` 의
    값을 읽어 ``code | category | 상품코드 | 상품명 | 매출 | 발주 | 매입 | 폐기 | 현재고``
    형식으로 ``output_file`` 경로에 한 줄씩 기록한다.
    """

    path = Path(output_file or (Path(__file__).resolve().parent.parent / "code_outputs/products.txt"))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    seen_codes: set[str] = set()

    for num in range(1, 901):
        code_str = f"{num:03}"
        element = driver.execute_script(
            """
return [...document.querySelectorAll('div')]
  .find(el => el.innerText?.trim() === arguments[0] &&
               el.id?.includes('cell_') && !el.id?.includes(':text'));
""",
            code_str,
        )

        if not element:
            log("category-skip", "INFO", f"'{code_str}' 셀 없음")
            continue

        dispatch_mouse_event(driver, element)
        prev_text = driver.execute_script(
            """
return document.querySelector("div[id*='gdDetail'][id*='gridrow_0'][id*='cell_0_0:text']")?.innerText?.trim() || '';
"""
        )

        if not wait_for_detail_grid(driver, timeout=5):
            log("detail-grid", "WARNING", f"'{code_str}' 상품 그리드 로딩 실패")
            continue

        if not grid_utils.wait_for_grid_update(driver, prev_text, timeout=6):
            log("detail-grid", "WARNING", f"'{code_str}' 상품 그리드 값 변화 없음")
            continue
        time.sleep(delay)

        row_index = driver.execute_script(
            """var m = arguments[0].id.match(/gridrow_(\\d+)/); return m ? m[1] : null;""",
            element,
        )
        category_name = driver.execute_script(
            """
var selector = `div[id*="gridrow_${arguments[0]}"][id*="cell_${arguments[0]}_1:text"]`;
var el = document.querySelector(selector);
return el?.innerText?.trim() || '';
""",
            row_index,
        )


        while True:
            text_cells = driver.execute_script(
                """
return [...document.querySelectorAll("div[id*='gdDetail'][id*='cell_'][id$='_0:text']")];
"""
            )
            row_count = len(text_cells)

            for row in range(row_count):
                row_el = driver.execute_script(
                    """
return [...document.querySelectorAll('div')]
  .find(el => el.id?.includes('gridrow_0') &&
               el.id?.includes('cell_' + arguments[0] + '_0') &&
               !el.id?.includes(':text'));
""",
                    row,
                )
                if row_el:
                    dispatch_mouse_event(driver, row_el)
                    time.sleep(delay)
                else:
                    log("row", "WARNING", f"row {row} 클릭 대상 없음")

                cols = grid_utils.get_product_row_texts(driver, row)
                product_code = cols[0]
                if not product_code or product_code in seen_codes:
                    continue
                seen_codes.add(product_code)

                for idx, text in enumerate(cols):
                    if text == "":
                        log("row", "WARNING", f"row {row} col {idx} 텍스트 없음 (빈 문자열 처리됨)")

                line = f"{code_str} | {category_name} | " + " | ".join(cols)
                with path.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")

            prev_text = driver.execute_script(
                "return document.querySelector(\"div[id*='gdDetail'][id*='gridrow_0'][id*='cell_0_0:text']\")?.innerText?.trim() || '';"
            )
            if click_scroll_button(driver) and grid_utils.wait_for_grid_update(driver, prev_text, timeout=6):
                time.sleep(delay)
                continue
            break
