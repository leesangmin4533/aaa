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

    ``text`` is compared in a case-insensitive manner and consecutive
    whitespace is ignored so that minor DOM text variations do not break the
    navigation flow. The function searches all DOM nodes and clicks the first
    matching element. ``True`` is returned on success, otherwise ``False``. Any
    exception is logged and swallowed.
    """

    try:
        target = " ".join(text.split()).lower()
        xpath = (
            "//*[contains(translate(normalize-space(.),"
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
