import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from selenium.webdriver.common.by import By
import logging

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.sales_analysis.navigate_to_mid_category import (
    click_codes_in_order,
    click_codes_by_arrow,
)


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
        MockWait.return_value.until_not.side_effect = lambda cond: True
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


def test_click_codes_by_arrow_clicks_until_repeat(caplog):
    first_cell = MagicMock()
    first_cell.text = "001"

    driver = MagicMock()

    def find_element_side_effect(by, value):
        if by == By.XPATH:
            return first_cell
        raise AssertionError(f"Unexpected lookup: {value}")

    driver.find_element.side_effect = find_element_side_effect

    active1 = MagicMock()
    active1.text = "002"
    active2 = MagicMock()
    active2.text = "003"
    active3 = MagicMock()
    active3.text = "002"  # repeat to stop

    active_iter = iter([active1, active2, active3])

    class DummyActions:
        def __init__(self, drv):
            self.drv = drv
        def send_keys(self, key):
            return self
        def perform(self):
            try:
                self.drv.switch_to.active_element = next(active_iter)
            except StopIteration:
                pass


    driver.switch_to.active_element = first_cell

    with patch(
        "modules.sales_analysis.navigate_to_mid_category.ActionChains",
        DummyActions,
    ), caplog.at_level(logging.INFO):
        click_codes_by_arrow(driver, delay=0, max_scrolls=5)

    assert first_cell.click.called
    assert active1.click.called
    assert active2.click.called
    assert active3.click.called

    summary_found = any(
        "총 클릭: 3건" in rec.getMessage() for rec in caplog.records
    )
    assert summary_found
