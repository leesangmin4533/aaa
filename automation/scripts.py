import os
import time
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .config import log


def run_script(driver, name: str, scripts_dir) -> Any:
    """Read a JavaScript file from ``scripts_dir`` and execute it."""
    script_full_path = os.path.join(scripts_dir, name)
    log.debug(f"Checking script existence: {script_full_path}", extra={"tag": "run_script"})
    if not os.path.exists(script_full_path):
        msg = f"script file not found: {script_full_path}"
        log.error(msg, extra={"tag": "run_script"})
        raise FileNotFoundError(msg)
    with open(script_full_path, "r", encoding="utf-8") as f:
        js = f.read()
    return driver.execute_script(js)


def wait_for_data(driver, timeout: int = 10) -> Any | None:
    """Poll for ``window.__parsedData__`` until available or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        data = driver.execute_script("return window.__parsedData__ || null")
        if data is not None:
            return data
        time.sleep(0.5)
    return None


def wait_for_mix_ratio_page(driver, timeout: int = 60) -> bool:
    """중분류별 매출 구성비 화면이 나타나고 데이터가 로드될 때까지 대기한다."""
    selector = "div[id*='gdList.body'][id*='cell_'][id$='_0:text']"
    log.debug(f"Waiting for mix ratio page grid with selector: {selector}", extra={"tag": "navigation"})
    try:
        # 그리드 요소가 나타날 때까지 대기
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        
        # 그리드에 실제 데이터가 로드될 때까지 대기
        WebDriverWait(driver, timeout).until(
            lambda d: len(element.text.strip()) > 0
        )
        
        log.debug("Mix ratio page grid and data found.", extra={"tag": "navigation"})
        return True
    except TimeoutException:
        log.error(f"Mix ratio page grid not found within {timeout} seconds.", extra={"tag": "navigation"}, exc_info=True)
        return False
    except Exception as e:
        log.error(f"An unexpected error occurred while waiting for mix ratio page: {e}", extra={"tag": "navigation"}, exc_info=True)
        return False
