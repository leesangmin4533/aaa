from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from .log_util import create_logger

log = create_logger("popup_util")


def close_nexacro_popups(driver: WebDriver, timeout: int = 5) -> None:
    """'닫기' 텍스트가 있는 모든 DOM 요소가 나타날 때까지 기다렸다가 클릭 이벤트를 발생시킨다."""

    # '닫기' 텍스트가 포함된 요소가 표시될 때까지 대기
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(
                "return [...document.querySelectorAll('*')].some(el => el.innerText?.trim() === '닫기');"
            )
        )
    except Exception as e:
        log("close", "WARNING", f"'닫기' 요소 대기 실패: {e}")

    js = """
try {
    const closeEls = [...document.querySelectorAll('*')].filter(el => el.innerText?.trim() === '닫기');
    if (closeEls.length > 0) {
        closeEls.forEach(el => {
            const rect = el.getBoundingClientRect();
            ['mousedown', 'mouseup', 'click'].forEach(type => {
                el.dispatchEvent(new MouseEvent(type, {
                    bubbles: true,
                    cancelable: true,
                    view: window,
                    clientX: rect.left + rect.width / 2,
                    clientY: rect.top + rect.height / 2
                }));
            });
        });
        return 'clicked:' + closeEls.length;
    }
    return 'not found';
} catch (e) {
    return 'error: ' + e.toString();
}
"""
    try:
        result = driver.execute_script(js)
        log("close", "INFO", f"팝업 처리 결과: {result}")
    except Exception as e:
        log("close", "ERROR", f"스크립트 실행 실패: {e}")
