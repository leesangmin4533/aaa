"""Utilities for closing pop-up windows during automation."""

from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver


# ``POPUP_CLOSE_SCRIPT`` was previously reserved for a JavaScript snippet to
# close pop-up windows. The Selenium-based approach in ``close_popups`` proved
# sufficient, so the constant has been removed.


def close_popups(driver: WebDriver) -> dict:
    """Detect and close login pop-ups using Selenium calls.

    The function searches for ``div`` elements whose ``id`` contains
    ``STCM230_P1``. If such a pop-up is visible it tries two strategies to
    locate the close button:

    1. Search for a descendant ``div`` whose text is exactly ``닫기``.
       When found, the element is clicked and the reason is set to
       ``"STCM230_P1 텍스트기반 닫기 성공"``.
    2. Fallback to searching for a descendant ``div`` containing the text
       ``닫기`` and the class ``btn``. This maintains compatibility with the
       previous behaviour.

    Parameters
    ----------
    driver:
        Selenium WebDriver instance.

    Returns
    -------
    dict
        A dictionary with ``detected`` and ``closed`` flags, the ``target``
        pop-up ``id`` and an optional ``reason`` when closing fails.
    """

    result = {
        "detected": False,
        "closed": False,
        "target": None,
        "reason": None,
    }

    # 0. Always present first popup (STZZ120_P0)
    try:
        fixed_popups = driver.find_elements(By.CSS_SELECTOR, "div[id*='STZZ120_P0']")
        for fixed in fixed_popups:
            if fixed.is_displayed():
                close_btn = fixed.find_element(By.XPATH, ".//div[contains(@id, 'btn_close')]")
                close_btn.click()
                result.update({
                    "detected": True,
                    "closed": True,
                    "target": fixed.get_attribute("id"),
                    "reason": "고정 팝업 STZZ120_P0 닫기 성공",
                })
                return result
    except Exception as e:
        result.update({
            "detected": True,
            "closed": False,
            "target": "STZZ120_P0",
            "reason": f"STZZ120_P0 닫기 실패: {e}",
        })
        return result

    # 1. Wait briefly for the pop-up to render after login
    sleep(1.0)

    try:
        popup_roots = driver.find_elements(By.CSS_SELECTOR, "div[id*='STCM230_P1']")
    except Exception as e:  # Safety net if query itself fails
        result["reason"] = str(e)
        return result

    for popup in popup_roots:
        try:
            if not popup.is_displayed():
                continue

            result["detected"] = True
            result["target"] = popup.get_attribute("id")

            # 1-A. Exact text match strategy
            text_match_btns = popup.find_elements(By.XPATH, ".//div[text()='닫기']")
            for btn in text_match_btns:
                if not btn.is_displayed():
                    continue
                try:
                    btn.click()
                    result.update({
                        "closed": True,
                        "reason": "STCM230_P1 텍스트기반 닫기 성공",
                    })
                    return result
                except Exception as e:
                    result["reason"] = f"버튼 클릭 실패: {e}"
                    return result

            # 1-B. Fallback previous strategy using class name
            close_btns = popup.find_elements(
                By.XPATH,
                ".//div[contains(text(), '닫기') and contains(@class, 'btn')]",
            )
            for btn in close_btns:
                if not btn.is_displayed():
                    continue
                try:
                    btn.click()
                    result["closed"] = True
                    return result
                except Exception as e:
                    result["reason"] = f"버튼 클릭 실패: {e}"
                    return result

        except Exception as e:  # Any issue while handling this popup
            result["reason"] = f"팝업 처리 실패: {e}"
            return result

    # If we reach here, either no pop-up was detected or closing failed
    if not result["detected"]:
        result["reason"] = "팝업 없음"
    else:
        result["reason"] = "닫기 버튼 없음"

    return result
