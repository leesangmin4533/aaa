import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import logging

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.sales_analysis.navigate_to_mid_category import click_codes_in_order


def test_click_codes_in_order_clicks_and_logs(caplog):
    # create mock grid rows with codes 1 and 3
    row1 = MagicMock()
    cell1 = MagicMock()
    cell1.text = "1"
    row1.find_element.return_value = cell1

    row2 = MagicMock()
    cell2 = MagicMock()
    cell2.text = "3"
    row2.find_element.return_value = cell2

    driver = MagicMock()
    driver.find_elements.return_value = [row1, row2]

    with patch('selenium.webdriver.support.ui.WebDriverWait') as MockWait, \
         patch('selenium.webdriver.support.expected_conditions.element_to_be_clickable') as mock_clickable:
        MockWait.return_value.until.side_effect = lambda cond: cond
        mock_clickable.side_effect = lambda el: el

        with caplog.at_level(logging.INFO):
            click_codes_in_order(driver, start=1, end=3)

    # verify cells 1 and 3 clicked
    assert cell1.click.called
    assert cell2.click.called

    # verify log message for missing code 2
    msg_found = any('코드 002 없음' in rec.getMessage() for rec in caplog.records)
    assert msg_found
