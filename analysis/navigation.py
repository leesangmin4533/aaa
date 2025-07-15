from __future__ import annotations

import time
from selenium.webdriver.remote.webdriver import WebDriver

from utils.log_util import create_logger

# 메뉴 버튼 고정 ID 상수
MAIN_MENU_ID = (
    "mainframe.HFrameSet00.VFrameSet00.FrameSet.WorkFrame.form.btn_saleAnalysis"
)

# '중분류별 매출 구성비' 버튼 ID
MIDDLE_MENU_ID = (
    "mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB010_M0.form.div_workForm.form.div2.form.div_search.form.btnMiddle"
)




def navigate_to_category_mix_ratio(driver: WebDriver) -> bool:
    log = create_logger("navigation")

    def click_by_id(el_id: str) -> bool:
        """주어진 ID의 요소를 찾아 클릭 이벤트를 전송한다."""

        return bool(
            driver.execute_script(
                r"""
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

    time.sleep(3.5)  # 메뉴가 동적으로 로드될 때까지 대기
    log("nav", "INFO", "🔍 '중분류별 매출 구성비' 클릭 시도")

    if not click_by_id(MIDDLE_MENU_ID):
        log("nav", "ERROR", "❌ '중분류별 매출 구성비' 클릭 실패")
        return False

    # 화면이 완전히 로드될 시간을 준다
    time.sleep(1)

    log("nav", "SUCCESS", "✅ 메뉴 진입 완료")
    return True
