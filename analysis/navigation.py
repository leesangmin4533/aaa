from __future__ import annotations

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from utils.log_util import create_logger

logger = create_logger("navigation")


def click_menu_by_text(driver: WebDriver, text: str, timeout: int = 5) -> bool:
    """Click a menu element matching ``text``.

    The function searches all DOM nodes for an element whose ``innerText`` matches
    ``text`` and clicks it using JavaScript. It returns ``True`` on success and
    ``False`` on failure. Exceptions are logged as warnings.
    """
    try:
        element = WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(
                "return [...document.querySelectorAll('*')]\n"
                "    .find(el => el.innerText?.trim() === arguments[0]) || null;",
                text,
            )
        )
        driver.execute_script("arguments[0].click()", element)
        return True
    except Exception as e:  # pragma: no cover - defensive
        logger("menu", "WARNING", f"click_menu_by_text failed: {e}")
        return False


def go_to_mix_ratio_screen(driver: WebDriver) -> bool:
    """Navigate to the mix ratio screen via menu clicks."""

    if not click_menu_by_text(driver, "영업분석"):
        return False
    if not click_menu_by_text(driver, "중분류별 매출구성비"):
        return False
    return True
