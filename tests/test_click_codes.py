import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from selenium.webdriver.common.by import By
import logging

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.sales_analysis.mid_category_clicker import (
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

    with patch('modules.sales_analysis.mid_category_clicker.WebDriverWait') as MockWait, \
         patch('modules.sales_analysis.mid_category_clicker.EC.element_to_be_clickable') as mock_clickable:
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
    cell1 = MagicMock()
    cell1.text = "001"
    cell1.get_attribute.return_value = "id1_0:text"

    cell2 = MagicMock()
    cell2.text = "002"
    cell2.get_attribute.return_value = "id2_0:text"

    cell3 = MagicMock()
    cell3.text = "002"
    cell3.get_attribute.return_value = "id3_0:text"

    cell4 = MagicMock()
    cell4.text = "002"
    cell4.get_attribute.return_value = "id4_0:text"

    driver = MagicMock()
    driver.find_elements.return_value = [cell1, cell2, cell3, cell4]

    with patch('modules.sales_analysis.mid_category_clicker.WebDriverWait') as MockWait, \
         patch('modules.sales_analysis.mid_category_clicker.EC.element_to_be_clickable') as mock_clickable, \
         caplog.at_level(logging.INFO):
        MockWait.return_value.until.side_effect = lambda cond: cond
        mock_clickable.side_effect = lambda el: el

        click_codes_by_arrow(driver, delay=0)

    assert cell1.click.called
    assert cell2.click.called
    assert cell3.click.called
    assert cell4.click.called

    summary_found = any(
        "총 클릭: 4건" in rec.getMessage() for rec in caplog.records
    )
    assert summary_found


def test_click_codes_by_arrow_sorts_and_skips(caplog):
    invalid = MagicMock()
    invalid.text = "AA"
    invalid.get_attribute.return_value = "id0_0:text"

    cell1 = MagicMock()
    cell1.text = "010"
    cell1.get_attribute.return_value = "id1_0:text"

    cell2 = MagicMock()
    cell2.text = "003"
    cell2.get_attribute.return_value = "id2_0:text"

    driver = MagicMock()
    driver.find_elements.return_value = [invalid, cell1, cell2]

    with patch('modules.sales_analysis.mid_category_clicker.WebDriverWait') as MockWait, \
         patch('modules.sales_analysis.mid_category_clicker.EC.element_to_be_clickable') as mock_clickable, \
         caplog.at_level(logging.INFO):
        MockWait.return_value.until.side_effect = lambda cond: cond
        mock_clickable.side_effect = lambda el: el

        click_codes_by_arrow(driver, delay=0)

    assert not invalid.click.called
    assert cell2.click.called
    assert cell1.click.called


def test_click_codes_by_arrow_retry_and_stop(caplog):
    cell1 = MagicMock()
    cell1.text = "001"
    cell1.get_attribute.return_value = "id1_0:text"
    cell1.click.side_effect = [Exception("fail"), None]

    cell2 = MagicMock()
    cell2.text = "002"
    cell2.get_attribute.return_value = "id2_0:text"
    cell2.click.side_effect = [Exception("fail"), Exception("fail"), Exception("fail")]

    driver = MagicMock()
    driver.find_elements.return_value = [cell1, cell2]

    with patch('modules.sales_analysis.mid_category_clicker.WebDriverWait') as MockWait, \
         patch('modules.sales_analysis.mid_category_clicker.EC.element_to_be_clickable') as mock_clickable, \
         caplog.at_level(logging.INFO):
        MockWait.return_value.until.side_effect = lambda cond: cond
        mock_clickable.side_effect = lambda el: el

        click_codes_by_arrow(driver, delay=0)

    assert cell1.click.call_count == 2
    assert cell2.click.call_count == 3
