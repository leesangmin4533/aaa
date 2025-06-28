import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.common.popup_utils import close_popups
from selenium.webdriver.common.by import By


def test_close_popups_no_popup():
    driver = Mock()
    driver.find_elements.return_value = []

    result = close_popups(driver)

    driver.find_elements.assert_called_once_with(By.CSS_SELECTOR, "div[id*='STCM230_P1']")
    assert result == {
        "detected": False,
        "closed": False,
        "target": None,
        "reason": "팝업 없음",
    }


def test_close_popups_closes_popup():
    close_btn = Mock()
    close_btn.is_displayed.return_value = True

    popup = Mock()
    popup.is_displayed.return_value = True
    popup.get_attribute.return_value = "popup_STCM230_P1"
    popup.find_elements.return_value = [close_btn]

    driver = Mock()
    driver.find_elements.return_value = [popup]

    result = close_popups(driver)

    driver.find_elements.assert_called_once_with(By.CSS_SELECTOR, "div[id*='STCM230_P1']")
    popup.find_elements.assert_called_once_with(
        By.XPATH,
        ".//div[contains(text(), '닫기') and contains(@class, 'btn')]",
    )
    close_btn.click.assert_called_once()

    assert result == {
        "detected": True,
        "closed": True,
        "target": "popup_STCM230_P1",
        "reason": None,
    }
