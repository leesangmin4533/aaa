from __future__ import annotations

import time
from selenium.webdriver.remote.webdriver import WebDriver

from utils.log_util import create_logger

# 메뉴 버튼 고정 ID 상수
MAIN_MENU_ID = (
    "mainframe.HFrameSet00.VFrameSet00.FrameSet.WorkFrame.form.btn_saleAnalysis"
)


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

    def click_by_id(el_id: str) -> bool:
        """주어진 ID의 요소를 찾아 클릭 이벤트를 전송한다."""

        return bool(
            driver.execute_script(
                """
const el = document.getElementById(arguments[0]);
if (!el) return false;
const r = el.getBoundingClientRect();
['mousedown','mouseup','click'].forEach(type =>
  el.dispatchEvent(new MouseEvent(type, {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: r.left + r.width / 2,
    clientY: r.top + r.height / 2
  }))
);
return true;
""",
                el_id,
            )
        )

    log("nav", "INFO", "🔍 '매출분석' 클릭 시도")
    if not click_by_id(MAIN_MENU_ID):
        log("nav", "ERROR", "❌ '매출분석' 클릭 실패")
        return False

    time.sleep(2)  # 메뉴 확장 시간 고려
    log("nav", "INFO", "🔍 '중분류별 매출 구성비' 클릭 시도")

    clicked = driver.execute_script(
        """
const txt = arguments[0].replace(/\s+/g, '').toLowerCase();
const snapshot = document.evaluate(
  "//div[contains(@class, 'nexatextitem')]",
  document,
  null,
  XPathResult.ORDERED_NODE_SNAPSHOT_TYPE,
  null
);
let target = null;
for (let i = 0; i < snapshot.snapshotLength; i++) {
  const el = snapshot.snapshotItem(i);
  if (!el) continue;
  const normalized = (el.innerText || '').replace(/\s+/g, '').toLowerCase();
  if (normalized.includes(txt) && el.offsetParent !== null) {
    target = el;
    break;
  }
}
if (!target) return false;
const r = target.getBoundingClientRect();
['mousedown','mouseup','click'].forEach(type =>
  target.dispatchEvent(new MouseEvent(type, {
    bubbles: true,
    cancelable: true,
    view: window,
    clientX: r.left + r.width / 2,
    clientY: r.top + r.height / 2
  }))
);
return true;
""",
        "중분류"
    )

    if not clicked:
        log("nav", "ERROR", "❌ '중분류별 매출 구성비' 클릭 실패")
        return False

    log("nav", "INFO", "⌛ 좌측 그리드 로딩 대기")
    if not _wait_for_list_grid(driver, timeout=5):
        log("nav", "ERROR", "❌ 좌측 그리드 로딩 실패")
        return False

    log("nav", "SUCCESS", "✅ 메뉴 진입 완료")
    return True
