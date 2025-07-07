"""Simple automation helpers for product grids."""

from __future__ import annotations

import time
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException

from . import grid_utils

__all__ = ["click_all_product_codes"]


def click_all_product_codes(
    driver: WebDriver,
    codes: list[str] | None = None,
    delay: float = 0.3,
    max_retry: int = 1,
) -> int:
    """Click product codes sequentially with retry on failure."""

    if codes is None:
        codes = [f"{i:03}" for i in range(1, 901)]

    clicked = 0

    for code in codes:
        attempts = 0
        while attempts <= max_retry:
            element = grid_utils.find_clickable_cell_by_code(driver, code)
            if element:
                try:
                    element.click()
                    clicked += 1
                    break
                except WebDriverException:
                    pass
            driver.execute_script("window.scrollBy(0, 100)")
            time.sleep(delay)
            attempts += 1

    return clicked
