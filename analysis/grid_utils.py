from selenium.webdriver.remote.webdriver import WebDriver
import time


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
