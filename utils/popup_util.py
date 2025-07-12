from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time

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
    const chkEls = [...document.querySelectorAll("img[src*='chk_WF_Box']")];
    chkEls.forEach(el => {
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


def close_focus_popup(driver: WebDriver, timeout: int = 5) -> None:
    """"재택 유선권장 안내" 팝업을 엔터 키로 닫는다."""

    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            popup = driver.find_element(By.XPATH, "//div[contains(text(), '재택 유선권장 안내')]")
            if popup.is_displayed():
                log("focus_popup", "INFO", "팝업 감지됨: 엔터로 종료 시도")
                ActionChains(driver).send_keys(Keys.ENTER).perform()
                log("focus_popup", "INFO", "엔터 키 전송 완료")
                return
        except Exception as e:
            log("focus_popup", "DEBUG", f"팝업 탐색 오류 또는 미표시: {e}")
        time.sleep(0.5)
    log("focus_popup", "DEBUG", "대상 팝업을 찾지 못함")


def ensure_focus_popup_closed(
    driver: WebDriver,
    timeout: int = 5,
    stable_time: float = 1.0,
) -> None:
    """"재택 유선권장 안내" 팝업이 다시 나타나지 않는지 확인하며 닫는다.

    ``stable_time`` 동안 팝업이 감지되지 않으면 종료된 것으로 간주한다.
    ``timeout`` 이내에 조건이 충족되지 않으면 경고 로그를 남긴다.
    """

    end_time = time.time() + timeout
    last_seen = time.time()

    while time.time() < end_time:
        try:
            popup = driver.find_element(
                By.XPATH, "//div[contains(text(), '재택 유선권장 안내')]"
            )
            if popup.is_displayed():
                log("focus_popup", "INFO", "팝업 감지됨: 엔터로 종료 시도")
                ActionChains(driver).send_keys(Keys.ENTER).perform()
                last_seen = time.time()
                log("focus_popup", "INFO", "엔터 키 전송 완료")
        except Exception:
            pass

        if time.time() - last_seen >= stable_time:
            log("focus_popup", "DEBUG", "팝업이 더 이상 나타나지 않음")
            return

        time.sleep(0.2)

    log("focus_popup", "WARNING", "타임아웃: 팝업 상태 불안정")

def close_popups_after_delegate(driver: WebDriver, timeout: int = 10) -> None:
    """TensorFlow Lite delegate 로그 이후 팝업을 다시 닫는다."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            logs = driver.get_log("browser")
        except Exception:
            logs = []
        for entry in logs:
            msg = entry.get("message", "") if isinstance(entry, dict) else str(entry)
            if "Created TensorFlow Lite XNNPACK delegate for CPU" in msg:
                close_focus_popup(driver)
                ensure_focus_popup_closed(driver)
                close_nexacro_popups(driver)
                log("delegate", "INFO", "팝업 모듈 처리 후 다음 단계 진입")
                return
        time.sleep(0.5)
