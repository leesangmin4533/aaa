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


def wait_for_mix_ratio_page(driver, timeout: int = 10) -> bool:
    """'중분류별 매출 구성비' 화면으로 이동하고, 데이터가 로드될 때까지 대기한다."""
    log.info("Navigating to '중분류별 매출 구성비' page...", extra={"tag": "navigation"})
    try:
        # 1. '매출분석' 상단 메뉴 클릭 (ID 기반)
        top_menu_js = """
        const topMenu = document.querySelector("div[id*='STMB000_M0:icontext']");
        if (!topMenu) return 'Top menu not found';
        const rect = topMenu.getBoundingClientRect();
        ['mousedown', 'mouseup', 'click'].forEach(evt => {
            topMenu.dispatchEvent(new MouseEvent(evt, {
                bubbles: true, cancelable: true, view: window,
                clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2
            }));
        });
        return true;
        """
        result = driver.execute_script(top_menu_js)
        if (result is not True):
            log.error(f"Failed to click top menu '매출분석': {result}", extra={"tag": "navigation"})
            return False
        log.debug("Clicked top menu '매출분석'. Waiting for submenu.", extra={"tag": "navigation"})
        time.sleep(1.5)

        # 2. '중분류별 매출 구성비' 서브 메뉴 클릭 (안정성 개선)
        sub_menu_js = """
        const menuContainer = document.querySelector("div[id*='pdiv_topMenu']");
        if (!menuContainer) return 'Sub menu container not found';

        const subMenu = [...menuContainer.querySelectorAll("div")].find(
            el => el.innerText.includes('중분류') && el.offsetParent !== null
        );
        if (!subMenu) return 'Sub menu with text \'중분류\' not found in container';

        const rect = subMenu.getBoundingClientRect();
        ['mousedown', 'mouseup', 'click'].forEach(evt => {
            subMenu.dispatchEvent(new MouseEvent(evt, {
                bubbles: true, cancelable: true, view: window,
                clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2
            }));
        });
        return true;
        """
        result = driver.execute_script(sub_menu_js)
        if (result is not True):
            log.error(f"Failed to click sub menu '중분류별 매출 구성비': {result}", extra={"tag": "navigation"})
            return False
        log.info("Successfully navigated. Now waiting for page grid to load.", extra={"tag": "navigation"})

        # 3. 페이지 그리드가 나타나고 데이터가 로드될 때까지 대기
        selector = "div[id*='gdList.body'][id*='cell_'][id$='_0:text']"
        log.debug(f"Waiting for mix ratio page grid with selector: {selector}", extra={"tag": "navigation"})

        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_element(By.CSS_SELECTOR, selector).text.strip()) > 0
        )

        log.debug("Mix ratio page grid and data found.", extra={"tag": "navigation"})
        return True
    except TimeoutException:
        log.error(f"Mix ratio page grid not found within {timeout} seconds after navigation.", extra={"tag": "navigation"}, exc_info=True)
        return False
    except Exception as e:
        log.error(f"An unexpected error occurred while navigating or waiting for mix ratio page: {e}", extra={"tag": "navigation"}, exc_info=True)
        return False
