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


def click_all_visible_product_codes(driver: WebDriver, seen: set[str]) -> int:
    """현재 화면에 렌더링된 상품코드 셀을 중복 없이 클릭한다.

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver instance.
    seen : set[str]
        이미 클릭한 상품코드들. 중복 방지용으로 갱신됨.

    Returns
    -------
    int
        새롭게 클릭된 상품코드 수
    """

    script = """
const seen = new Set(arguments[1]);
const clicked = [];

const textCells = [...document.querySelectorAll("div[id*='gdDetail.body'][id*='gridrow_'][id*='cell_'][id$='_0:text']")]
  .filter(el => /^\\d{13}$/.test(el.innerText?.trim()));

for (const textEl of textCells) {
  const code = textEl.innerText.trim();
  if (seen.has(code)) continue;

  const clickId = textEl.id.replace(":text", "");
  const clickEl = document.getElementById(clickId);
  if (!clickEl) continue;

  const rect = clickEl.getBoundingClientRect();
  ['mousedown', 'mouseup', 'click'].forEach(type => {
    clickEl.dispatchEvent(new MouseEvent(type, {
      bubbles: true,
      cancelable: true,
      view: window,
      clientX: rect.left + rect.width / 2,
      clientY: rect.top + rect.height / 2
    }));
  });

  seen.add(code);
  clicked.push(code);
}

return clicked;
"""
    new_codes: list[str] = driver.execute_script(script, list(seen))
    seen.update(new_codes)
    return len(new_codes)
