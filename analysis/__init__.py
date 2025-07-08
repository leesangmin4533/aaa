"""Simple automation helpers for product grids.

이 모듈은 실제 서비스 환경에서 동작하는 여러 자동화 기능의 최소 구현체다.
테스트를 위해 필요한 함수만 간단히 정의되어 있으며, 나머지 함수는
예제 수준의 동작을 한다.
"""

from __future__ import annotations

import time
from typing import Any

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException

from . import grid_utils
from .navigation import navigate_to_category_mix_ratio
from utils.log_util import create_logger

__all__ = [
    "click_all_product_codes",
    "navigate_to_category_mix_ratio",
    "parse_mix_ratio_data",
    "extract_product_info",
]


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




def parse_mix_ratio_data(driver: WebDriver):
    """Parse grid data and return a DataFrame.

    Nexacro 그리드에서 중분류 코드와 명칭을 추출하여 ``pandas.DataFrame`` 으로
    반환한다. 실패 시 ``None`` 을 반환한다.
    """

    logger = create_logger("analysis")
    logger("parse", "DEBUG", "parse_mix_ratio_data start")

    js = """
try {
    const rows = [];
    const pattern = /^gdList\.gridrow_(\d+)$/;
    const els = [...document.querySelectorAll('div[id^="gdList.gridrow_"]')];
    els.forEach(el => {
        const m = el.id.match(pattern);
        if (!m) return;
        const idx = m[1];
        const code = document.querySelector(
            `div[id="gdList.gridrow_${idx}.cell_${idx}_0:text"]`
        );
        if (!code) return;
        const name = document.querySelector(
            `div[id="gdList.gridrow_${idx}.cell_${idx}_1:text"]`
        );
        rows.push({
            code: code.innerText.trim(),
            name: name ? name.innerText.trim() : null,
        });
    });
    return rows;
} catch (e) {
    return 'error:' + e.toString();
}
"""

    try:
        result: Any = driver.execute_script(js)
    except Exception as e:
        logger("parse", "ERROR", f"script failed: {e}")
        return None

    if isinstance(result, str) and result.startswith("error"):
        logger("parse", "ERROR", result)
        return None

    try:
        import pandas as pd
        df = pd.DataFrame(result)
    except Exception as e:
        logger("parse", "ERROR", f"DataFrame error: {e}")
        return None

    return df


def extract_product_info(driver: WebDriver) -> None:
    """Extract product information from the page.

    Selenium 동작 예시만 제공하고 실질적인 처리는 하지 않는다.
    """

    logger = create_logger("analysis")
    logger("product", "DEBUG", "extract_product_info stub called")
