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


def wait_for_mix_ratio_page(driver, timeout: int = 30) -> bool:
    """'중분류별 매출 구성비' 화면으로 이동한다."""
    log.info("Navigating to '중분류별 매출 구성비' page...", extra={"tag": "navigation"})
    try:
        # 1. '매출분석' 상단 메뉴 클릭
        top_menu_selector = r"#mainframe\.HFrameSet00\.VFrameSet00\.TopFrame\.form\.div_topMenu\.form\.STMB000_M0\:icontext"
        log.debug(f"Waiting for top menu with selector: {top_menu_selector}", extra={"tag": "navigation"})
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, top_menu_selector))
        )
        top_menu_js = r"""
        const topMenu = document.querySelector("#mainframe\.HFrameSet00\.VFrameSet00\.TopFrame\.form\.div_topMenu\.form\.STMB000_M0\:icontext");
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
        if result is not True:
            log.error(f"Failed to click top menu '매출분석': {result}", extra={"tag": "navigation"})
            return False
        log.debug("Clicked top menu '매출분석'. Waiting for submenu.", extra={"tag": "navigation"})
        time.sleep(1.5) # 메뉴가 나타날 때까지 잠시 대기

        # 2. '중분류별 매출 구성비' 서브 메뉴 클릭
        sub_menu_selector = r"#mainframe\.HFrameSet00\.VFrameSet00\.TopFrame\.form\.pdiv_topMenu_STMB000_M0\.form\.STMB011_M0\:text"
        log.debug(f"Waiting for sub menu with selector: {sub_menu_selector}", extra={"tag": "navigation"})
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, sub_menu_selector))
        )
        sub_menu_js = r"""
        const subMenu = document.querySelector("#mainframe\.HFrameSet00\.VFrameSet00\.TopFrame\.form\.pdiv_topMenu_STMB000_M0\.form\.STMB011_M0\:text");
        if (!subMenu) return 'Sub menu not found';
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
        if result is not True:
            log.error(f"Failed to click sub menu '중분류별 매출 구성비': {result}", extra={"tag": "navigation"})
            return False
        log.info("Successfully clicked '중분류별 매출 구성비'. Navigation complete.", extra={"tag": "navigation"})

        return True
    except TimeoutException:
        log.error(f"Navigation timed out.", extra={"tag": "navigation"}, exc_info=True)
        return False
    except Exception as e:
        log.error(f"An unexpected error occurred during navigation: {e}", extra={"tag": "navigation"}, exc_info=True)
        return False
