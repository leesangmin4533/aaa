import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import logging

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.sales_analysis.navigate_to_mid_category import click_codes_in_order


def test_click_codes_in_order_clicks_and_logs(caplog):
    # create mock grid rows with ids that map to codes 1 and 3
    row1 = MagicMock()
    row1.get_attribute.return_value = "row1.cell_0_0"
    cell1 = MagicMock()
    cell1.text = "1"

    row2 = MagicMock()
    row2.get_attribute.return_value = "row2.cell_0_0"
    cell2 = MagicMock()
    cell2.text = "3"

    driver = MagicMock()
    driver.find_elements.return_value = [row1, row2]

    def find_element_side_effect(by, value):
        if value == "row1.cell_0_0:text":
            return cell1
        if value == "row2.cell_0_0:text":
            return cell2
        raise AssertionError(f"Unexpected id lookup: {value}")

    driver.find_element.side_effect = find_element_side_effect

    with patch('selenium.webdriver.support.ui.WebDriverWait') as MockWait, \
         patch('selenium.webdriver.support.expected_conditions.element_to_be_clickable') as mock_clickable:
        MockWait.return_value.until.side_effect = lambda cond: cond
        mock_clickable.side_effect = lambda el: el

        with caplog.at_level(logging.INFO):
            click_codes_in_order(driver, start=1, end=3)

    # verify cells 1 and 3 clicked
    assert cell1.click.called
    assert cell2.click.called

    # verify row count log
    row_log = any("총 행 수: 2" in rec.getMessage() for rec in caplog.records)
    assert row_log

    # verify summary log message
    summary_found = any(
        '전체 3 중 클릭 성공 2건, 없음 1건' in rec.getMessage() for rec in caplog.records
    )
    assert summary_found
