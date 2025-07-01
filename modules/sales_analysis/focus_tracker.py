from selenium.webdriver.remote.webdriver import WebDriver

from .grid_click_logger import log_detail


def highlight_active_element(
    driver: WebDriver,
    color: str = "red",
    thickness: str = "2px",
    log_path: str = "grid_click_log.txt",
):
    """Outline the current active element and log its ID.

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver instance.
    color : str, optional
        Outline color.
    thickness : str, optional
        Outline thickness.
    log_path : str, optional
        Path of the log file used by :func:`log_detail`.

    Returns
    -------
    str | None
        ID of the active element if found, otherwise ``None``.
    """
    try:
        elem = driver.execute_script("return document.activeElement")
    except Exception as e:
        log_detail(f"❌ activeElement 조회 실패: {e}", log_path=log_path)
        return None

    if not elem:
        log_detail("⚠ activeElement 없음", log_path=log_path)
        return None

    style = f"{thickness} solid {color}"
    try:
        driver.execute_script("arguments[0].style.outline=arguments[1]", elem, style)
    except Exception:
        pass

    elem_id = elem.get_attribute("id")
    log_detail(f"현재 포커스: {elem_id}", log_path=log_path)
    return elem_id
