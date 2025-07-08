from __future__ import annotations

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import time

from utils.log_util import create_logger

logger = create_logger("navigation")


def click_menu_by_text(driver: WebDriver, text: str, timeout: int = 10) -> bool:
    """Click a menu element containing ``text``.

    Nexacro 메뉴는 텍스트가 ``div.nexatextitem`` 안에 위치하므로 해당 노드를
    대상으로 검색한다. ``text`` 는 대소문자를 구분하지 않고 연속된 공백을
    하나로 간주하여 비교한다. 일치하는 첫 번째 요소를 클릭하며, 예외가 발생
    하면 ``False`` 를 반환하고 로그만 남긴다.
    """

    try:
        target = " ".join(text.split()).lower()
        xpath = (
            "//div[contains(@class, 'nexatextitem') and "
            "contains(translate(normalize-space(.),"
            " 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'),"
            f" '{target}')]"
        )

        element = WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located((By.XPATH, xpath))
        )

        time.sleep(0.5)
        driver.execute_script("arguments[0].click()", element)
        return True
    except Exception as e:  # pragma: no cover - defensive
        logger("menu", "WARNING", f"click_menu_by_text failed: {type(e).__name__}: {e}")
        return False


def go_to_mix_ratio_screen(driver: WebDriver) -> bool:
    """Navigate to the mix ratio screen via menu clicks."""

    if not click_menu_by_text(driver, "매출분석"):
        return False
    if not click_menu_by_text(driver, "중분류별 매출 구성비"):
        return False
    return True
