import sys
from pathlib import Path
from unittest.mock import Mock, call

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.common.popup_utils import close_popups
from selenium.webdriver.common.by import By


def test_close_popups_no_popup():
    driver = Mock()
    driver.find_elements.side_effect = [[], []]

    result = close_popups(driver)

    assert driver.find_elements.call_args_list == [
        call(By.CSS_SELECTOR, "div[id*='STZZ120_P0']"),
        call(By.CSS_SELECTOR, "div[id*='STCM230_P1']"),
    ]
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
    driver.find_elements.side_effect = [[], [popup]]

    result = close_popups(driver)

    assert driver.find_elements.call_args_list == [
        call(By.CSS_SELECTOR, "div[id*='STZZ120_P0']"),
        call(By.CSS_SELECTOR, "div[id*='STCM230_P1']"),
    ]
    popup.find_elements.assert_called_once_with(By.XPATH, ".//div[text()='닫기']")
    close_btn.click.assert_called_once()

    assert result == {
        "detected": True,
        "closed": True,
        "target": "popup_STCM230_P1",
        "reason": "STCM230_P1 텍스트기반 닫기 성공",
    }


def test_close_fixed_popup():
    close_btn = Mock()

    fixed_popup = Mock()
    fixed_popup.is_displayed.return_value = True
    fixed_popup.get_attribute.return_value = "popup_STZZ120_P0"
    fixed_popup.find_element.return_value = close_btn

    driver = Mock()
    driver.find_elements.side_effect = [[fixed_popup]]

    result = close_popups(driver)

    driver.find_elements.assert_called_once_with(By.CSS_SELECTOR, "div[id*='STZZ120_P0']")
    fixed_popup.find_element.assert_called_once_with(By.XPATH, ".//div[contains(@id, 'btn_close')]")
    close_btn.click.assert_called_once()

    assert result == {
        "detected": True,
        "closed": True,
        "target": "popup_STZZ120_P0",
        "reason": "고정 팝업 STZZ120_P0 닫기 성공",
    }
