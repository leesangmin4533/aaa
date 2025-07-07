from selenium.webdriver.remote.webdriver import WebDriver
import time

from utils.log_util import create_logger

log = create_logger("grid_utils")


def get_product_row_texts(driver: WebDriver, row: int, col_count: int = 7) -> list[str]:
    """Return text values for a product row in ``gdDetail``.

    Parameters
    ----------
    driver : WebDriver
        Active Selenium driver instance.
    row : int
        Row index within the grid.
    col_count : int, default 7
        Number of columns to read.
    """
    values: list[str] = []
    for col in range(col_count):
        text = driver.execute_script(
            """
var selector = `div[id*='gdDetail'] div[id*='gridrow_0'][id*='cell_${arguments[0]}_${arguments[1]}:text']`;
var el = document.querySelector(selector);
return el?.innerText?.trim() || "";
""",
            row,
            col,
        )
        values.append(text)
    return values


def wait_for_grid_update(driver: WebDriver, prev_value: str, timeout: float = 6.0) -> bool:
    """Wait until the first cell value of ``gdDetail`` changes."""
    end = time.time() + timeout
    while time.time() < end:
        curr = driver.execute_script(
            "return document.querySelector(\"div[id*='gdDetail'] div[id*='gridrow_0'][id*='cell_0_0:text']\")?.innerText?.trim() || '';"
        )
        if curr != prev_value and curr:
            return True
        time.sleep(0.3)
    return False


def click_all_visible_product_codes(driver: WebDriver) -> int:
    """현재 화면에 보이는 상품코드 셀을 모두 클릭한다.

    ``window.__clickedProductCodes`` 집합을 통해 이미 클릭한 코드를 관리하며
    새롭게 클릭된 코드의 개수를 반환한다. 스크롤 직후 렌더링 지연을 고려해
    첫 탐색에서 셀이 없으면 0.5초 뒤 한 번 더 시도한다.
    """

    def _run_js() -> list[str]:
        script = r"""
const seen = window.__clickedProductCodes = window.__clickedProductCodes || new Set();
const clicked = [];

const cells = [...document.querySelectorAll('div[id]')]
  .filter(el => el.id.includes('gdDetail') && el.id.endsWith(':text') &&
                /^\d{13}$/.test(el.innerText?.trim()));

for (const textEl of cells) {
  const code = textEl.innerText.trim();
  if (seen.has(code)) continue;
  const clickEl = document.getElementById(textEl.id.replace(':text', ''));
  if (!clickEl) continue;

  const r = clickEl.getBoundingClientRect();
  ['mousedown', 'mouseup', 'click'].forEach(type => {
    clickEl.dispatchEvent(new MouseEvent(type, {
      bubbles: true,
      cancelable: true,
      view: window,
      clientX: r.left + r.width / 2,
      clientY: r.top + r.height / 2
    }));
  });

  seen.add(code);
  clicked.push(code);
}
return clicked;
"""
        return driver.execute_script(script)

    new_codes = _run_js()
    if not new_codes:
        time.sleep(0.5)
        new_codes = _run_js()

    return len(new_codes)


def wait_until_clickable(driver: WebDriver, click_id: str, timeout: int = 3):
    """Return element when ``click_id`` exists and is visible within timeout."""
    end = time.time() + timeout
    while time.time() < end:
        element = driver.execute_script(
            "var el = document.getElementById(arguments[0]);"
            "return el && el.offsetParent !== null ? el : null;",
            click_id,
        )
        if element:
            return element
        time.sleep(0.1)
    return None


def find_clickable_cell_by_code(driver: WebDriver, code: str):
    """Locate clickable grid cell for a given code.

    Parameters
    ----------
    driver : WebDriver
        Active Selenium instance.
    code : str
        Code text to search for.
    """

    text_el = driver.execute_script(
        """
return [...document.querySelectorAll('div[id*="gdList"][id*="cell_"][id$="_0:text"]')]
  .find(el => el.innerText?.trim() === arguments[0]);
""",
        code,
    )
    if not text_el:
        return None
    click_id = driver.execute_script("return arguments[0].id.replace(':text', '')", text_el)
    return wait_until_clickable(driver, click_id)
