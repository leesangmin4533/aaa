from selenium.webdriver.remote.webdriver import WebDriver

from .log_util import create_logger

log = create_logger("popup_util")


def close_nexacro_popups(driver: WebDriver) -> None:
    """Close Nexacro popups by simulating a DOM click on elements with text '닫기'."""
    js = """
try {
    const closeEl = [...document.querySelectorAll('*')].find(el => el.innerText?.trim() === '닫기');
    if (closeEl) {
        const rect = closeEl.getBoundingClientRect();
        ['mousedown', 'mouseup', 'click'].forEach(type => {
            closeEl.dispatchEvent(new MouseEvent(type, {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: rect.left + rect.width / 2,
                clientY: rect.top + rect.height / 2
            }));
        });
        return 'clicked';
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
