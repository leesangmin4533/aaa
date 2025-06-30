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
    first_cell = MagicMock()
    first_cell.text = "001"
    first_cell.get_attribute.return_value = (
        "prefix.gdList.body.gridrow_0.cell_0_0:text"
    )

    cell1 = MagicMock()
    cell1.text = "002"
    cell2 = MagicMock()
    cell2.text = "002"
    cell3 = MagicMock()
    cell3.text = "002"  # third time triggers stop

    calls = iter([cell1, cell2, cell3])

    driver = MagicMock()

    def find_element_side_effect(by, value):
        if by == By.XPATH:
            return first_cell
        if by == By.ID:
            return next(calls)
        raise AssertionError(f"Unexpected lookup: {value}")

    driver.find_element.side_effect = find_element_side_effect

    class DummyActions:
        def __init__(self, drv):
            self.drv = drv
        def move_to_element(self, el):
            return self
        def click(self, el=None):
            return self
        def send_keys(self, key):
            return self
        def perform(self):
            pass

    with patch(
        "modules.sales_analysis.mid_category_clicker.ActionChains",
        DummyActions,
    ), caplog.at_level(logging.INFO):
        click_codes_by_arrow(driver, delay=0, max_scrolls=5, retry_delay=0)

    assert first_cell.click.called
    assert cell1.click.called
    assert cell2.click.called
    assert cell3.click.called

    summary_found = any(
        "총 클릭: 4건" in rec.getMessage() for rec in caplog.records
    )
    assert summary_found

    final_found = any(
        "최종 종료" in rec.getMessage() and "마지막 코드" in rec.getMessage()
        for rec in caplog.records
    )
    assert final_found


def test_click_codes_by_arrow_rescroll_on_missing_cell(caplog):
    first_cell = MagicMock()
    first_cell.text = "001"
    first_cell.get_attribute.return_value = (
        "prefix.gdList.body.gridrow_0.cell_0_0:text"
    )

    cell1 = MagicMock()
    cell1.text = "002"
    cell2 = MagicMock()
    cell2.text = "003"

    call_counts = {"cell1": 0}

    driver = MagicMock()

    def find_element_side_effect(by, value):
        if by == By.XPATH:
            return first_cell
        if by == By.ID:
            if value == "prefix.gdList.body.gridrow_1.cell_1_0:text":
                call_counts["cell1"] += 1
                if call_counts["cell1"] == 1:
                    raise Exception("not loaded")
                return cell1
            if value == "prefix.gdList.body.gridrow_2.cell_2_0:text":
                return cell2
        raise AssertionError(f"Unexpected lookup: {value}")

    driver.find_element.side_effect = find_element_side_effect

    class DummyActions:
        def __init__(self, drv):
            pass
        def move_to_element(self, el):
            return self
        def click(self, el=None):
            return self

        def send_keys(self, key):
            return self

        def perform(self):
            pass

    with patch(
        "modules.sales_analysis.mid_category_clicker.ActionChains",
        DummyActions,
    ), caplog.at_level(logging.INFO):
        click_codes_by_arrow(driver, delay=0, max_scrolls=3, retry_delay=0)

    assert call_counts["cell1"] == 1
    assert first_cell.click.called
    assert not cell1.click.called
    assert not cell2.click.called


def test_click_codes_by_arrow_focus_recovery(caplog):
    first_cell = MagicMock()
    first_cell.text = "001"
    first_cell.get_attribute.return_value = (
        "prefix.gdList.body.gridrow_0.cell_0_0:text"
    )

    cell1 = MagicMock()
    cell1.text = "002"

    id_calls = {"cnt": 0}

    driver = MagicMock()

    last_id = first_cell.get_attribute.return_value

    def find_element_side_effect(by, value):
        if by == By.XPATH:
            return first_cell
        if by == By.ID:
            if value == "prefix.gdList.body.gridrow_1.cell_1_0:text":
                id_calls["cnt"] += 1
                if id_calls["cnt"] == 1:
                    raise Exception("not ready")
                return cell1
            if value == "prefix.gdList.body.gridrow_2.cell_2_0:text":
                return cell1
            if value == last_id:
                return first_cell
        raise AssertionError(f"Unexpected lookup: {value}")

    driver.find_element.side_effect = find_element_side_effect

    invalid_el = MagicMock()
    invalid_el.get_attribute.return_value = "mainframe"
    driver.switch_to.active_element = invalid_el

    class DummyActions:
        def __init__(self, drv):
            pass
        def move_to_element(self, el):
            return self
        def click(self, el=None):
            return self

        def send_keys(self, key):
            return self

        def perform(self):
            pass

    with patch(
        "modules.sales_analysis.mid_category_clicker.ActionChains",
        DummyActions,
    ), caplog.at_level(logging.INFO):
        click_codes_by_arrow(driver, delay=0, max_scrolls=1, retry_delay=0)

    assert cell1.click.called
    recovery_logged = any(
        "포커스 복구 성공" in rec.getMessage() for rec in caplog.records
    )
    assert recovery_logged
