"""Simple automation helpers for product grids.

이 모듈은 실제 서비스 환경에서 동작하는 여러 자동화 기능의 최소 구현체다.
테스트를 위해 필요한 함수만 간단히 정의되어 있으며, 나머지 함수는
예제 수준의 동작을 한다.
"""

from __future__ import annotations

import time
from typing import Any

from selenium.webdriver.remote.webdriver import WebDriver

from pathlib import Path
from .navigation import navigate_to_category_mix_ratio
from .product_exporter import export_product_data, HEADER
from utils.log_util import create_logger

__all__ = [
    "click_all_product_codes",
    "navigate_to_category_mix_ratio",
    "parse_mix_ratio_data",
    "extract_product_info",
    "export_product_data",
]


def click_all_product_codes(
    driver: WebDriver,
    script_path: str | None = None,
) -> None:
    """Run the JavaScript auto clicker inside the browser."""

    logger = create_logger("analysis")

    if script_path is None:
        script_path = str(Path(__file__).with_name("grid_auto_clicker.js"))

    try:
        with open(script_path, "r", encoding="utf-8") as f:
            js = f.read()
    except OSError as e:
        logger("click", "ERROR", f"script load failed: {e}")
        raise

    driver.execute_script(js)




def parse_mix_ratio_data(driver: WebDriver):
    """Return category codes as a ``pandas.DataFrame``.

    Nexacro 그리드에서 중분류 코드와 명칭을 추출하여 ``pandas.DataFrame`` 으로
    반환한다. 그리드 로딩을 확인하기 위해 최대 3초간 대기하며,
    실패 시 ``None`` 을 반환한다.
    """

    logger = create_logger("analysis")
    logger("parse", "DEBUG", "parse_mix_ratio_data start")

    js = r"""
try {
    const rows = [];
    const pattern = /gridrow_(\d+)/;
    const els = [...document.querySelectorAll("div[id*='gdList.body'][id*='gridrow_']")];
    els.forEach(el => {
        const m = el.id.match(pattern);
        if (!m) return;
        const idx = m[1];
        const code = document.querySelector(
            `div[id*='gdList.body'][id*='cell_${idx}_0'][id$=':text']`
        );
        if (!code) return;
        const name = document.querySelector(
            `div[id*='gdList.body'][id*='cell_${idx}_1'][id$=':text']`
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

    # 중분류를 클릭한 직후에는 상품 셀이 바로 렌더링되지 않을 수 있으므로
    # 셀 DOM이 나타날 때까지 최대 3초간 폴링한다.
    try:
        loaded: bool = driver.execute_async_script(
            """
  const callback = arguments[arguments.length - 1];
  let tries = 0;
  const max = 15;
  const wait = () => {
    const el = document.querySelector("div[id*='gdDetail.body'][id*='cell_0_0'][id$=':text']");
    if (el && el.innerText.trim()) {
      callback(true);
    } else if (++tries < max) {
      setTimeout(wait, 200);
    } else {
      callback(false);  // timeout
    }
  };
  wait();
"""
        )
        if not loaded:
            logger("parse", "WARNING", "상품 셀 로딩 대기 실패")
    except Exception as e:
        logger("parse", "ERROR", f"polling script failed: {e}")

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


def extract_product_info(driver: WebDriver, timeout: int = 3):
    """Extract product information from the product grid.

    Parameters
    ----------
    driver:
        Selenium WebDriver instance.
    timeout:
        Maximum seconds to wait for the first cell to appear.

    Returns
    -------
    list[dict[str, str]] | None
        추출한 행 데이터 목록. 실패 시 ``None`` 을 반환한다.
    """

    logger = create_logger("analysis")

    end_time = time.time() + timeout
    attempt = 1
    while time.time() < end_time:
        try:
            exists = driver.execute_script(
                "return document.querySelector(\"div[id*='gdDetail.body'][id*='cell_0_0'][id$=':text']\") !== null;"
            )
            logger("product", "DEBUG", f"셀 로딩 확인 시도 {attempt}: {exists}")
        except Exception as e:
            logger("product", "ERROR", f"load check failed: {e}")
            return None
        if exists:
            logger("product", "INFO", "상품 셀 로딩 완료")
            break
        time.sleep(0.5)
        attempt += 1
    else:
        logger("product", "WARNING", "상품 그리드 로딩 실패")
        return None

    js = r"""
try {
    const header = arguments[0];
    const out = [];
    for (let r = 0; ; r++) {
        const firstCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${r}_0'][id$=':text']`);
        if (!firstCell) break;
        const row = {};
        for (let c = 0; c < header.length - 2; c++) {
            const cell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${r}_${c}'][id$=':text']`);
            row[header[c + 2]] = cell ? cell.innerText.trim() : "";
        }
        out.push(row);
    }
    return out;
} catch (e) {
    return 'error:' + e.toString();
}
"""

    try:
        rows: Any = driver.execute_script(js, HEADER)
    except Exception as e:
        logger("product", "ERROR", f"script failed: {e}")
        return None

    if isinstance(rows, str) and rows.startswith("error"):
        logger("product", "ERROR", rows)
        return None

    return rows
