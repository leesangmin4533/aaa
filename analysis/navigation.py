from __future__ import annotations

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

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
        element = WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(
                "const target = arguments[0].replace(/\\s+/g, ' ').trim().toLowerCase();"
                "return [...document.querySelectorAll('*')]\n"
                "  .find(el => {\n"
                "    const t = (el.innerText || '').replace(/\\s+/g, ' ').trim().toLowerCase();\n"
                "    return t.includes(target);\n"
                "  }) || null;",
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

    if not click_menu_by_text(driver, "매출분석"):
        return False
    if not click_menu_by_text(driver, "중분류별 매출 구성비"):
        return False
    return True
