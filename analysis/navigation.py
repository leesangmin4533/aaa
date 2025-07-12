from __future__ import annotations

import time
from selenium.webdriver.remote.webdriver import WebDriver

from utils.log_util import create_logger


def _wait_for_list_grid(driver: WebDriver, timeout: int = 5) -> bool:
    """좌측 그리드 셀이 표시될 때까지 대기한다."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            exists = driver.execute_script(
                "return document.querySelector(\"div[id*='gdList.body'][id$='_0:text']\") !== null"
            )
            if exists:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def navigate_to_category_mix_ratio(driver: WebDriver) -> bool:
    log = create_logger("navigation")

    def click_by_text(text, wait=0.5, max_retry=10):
        for _ in range(max_retry):
            el = driver.execute_script("""
return [...document.querySelectorAll('div')].find(el =>
  el.innerText?.trim() === arguments[0] &&
  el.offsetParent !== null);
""", text)
            if el:
                driver.execute_script("""
var rect = arguments[0].getBoundingClientRect();
['mousedown', 'mouseup', 'click'].forEach(type => {
  arguments[0].dispatchEvent(new MouseEvent(type, {
    bubbles: true, cancelable: true, view: window,
    clientX: rect.left + rect.width / 2,
    clientY: rect.top + rect.height / 2
  }));
});
""", el)
                return True
            time.sleep(wait)
        return False

    log("nav", "INFO", "🔍 '매출분석' 클릭 시도")
    if not click_by_text("매출분석"):
        log("nav", "ERROR", "❌ '매출분석' 클릭 실패")
        return False

    time.sleep(2)  # 메뉴 확장 시간 고려
    log("nav", "INFO", "🔍 '중분류별 매출 구성비' 클릭 시도")
    if not click_by_text("중분류별 매출 구성비"):
        log("nav", "ERROR", "❌ '중분류별 매출 구성비' 클릭 실패")
        return False

    log("nav", "INFO", "⌛ 좌측 그리드 로딩 대기")
    if not _wait_for_list_grid(driver, timeout=5):
        log("nav", "ERROR", "❌ 좌측 그리드 로딩 실패")
        return False

    log("nav", "SUCCESS", "✅ 메뉴 진입 완료")
    return True
