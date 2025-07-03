import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.common.wait_utils import wait_and_click_cell
from selenium.webdriver.common.by import By


def test_wait_and_click_cell_waits_and_clicks():
    driver = MagicMock()
    with patch('modules.common.wait_utils.WebDriverWait') as MockWait, patch('modules.common.wait_utils.EC') as MockEC:
        instance = MockWait.return_value
        instance.until.side_effect = [None, None]
        condition_presence = MagicMock()
        condition_clickable = MagicMock()
        MockEC.presence_of_element_located.return_value = condition_presence
        MockEC.element_to_be_clickable.return_value = condition_clickable

        wait_and_click_cell(driver, 'cell', timeout=5)

        MockWait.assert_called_with(driver, 5)
        instance.until.assert_any_call(condition_presence)
        instance.until.assert_any_call(condition_clickable)
    driver.find_element.assert_called_once_with(By.ID, 'cell')

