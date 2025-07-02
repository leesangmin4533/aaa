import sys
from pathlib import Path
from unittest.mock import MagicMock
from selenium.common.exceptions import NoSuchElementException
import logging

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.sales_analysis.mid_category_clicker as mid_clicker


def test_click_codes_by_arrow_stops_after_repeat(caplog):
    cell1 = MagicMock()
    cell1.text = "001"
    cell1.get_attribute.return_value = "gdList.body.gridrow_0.cell_0_0"

    cell2 = MagicMock()
    cell2.text = "002"
    cell2.get_attribute.return_value = "gdList.body.gridrow_1.cell_0_0"

    cell3 = MagicMock()
    cell3.text = "002"
    cell3.get_attribute.return_value = "gdList.body.gridrow_2.cell_0_0"

    cell4 = MagicMock()
    cell4.text = "002"
    cell4.get_attribute.return_value = "gdList.body.gridrow_3.cell_0_0"

    cells = [cell1, cell2, cell3, cell4]

    class DummySwitch:
        def __init__(self, elements):
            self.elements = elements
            self.index = 0

        @property
        def active_element(self):
            return self.elements[self.index]

        def next(self):
            if self.index < len(self.elements) - 1:
                self.index += 1

    switch = DummySwitch(cells)

    def fake_send_arrow_down_native(driver):
        switch.next()



    class DummyActions:
        def __init__(self, driver):
            self.driver = driver
            self.element = None

        def move_to_element(self, element):
            self.element = element
            return self

        def click(self, element=None):
            target = element or self.element
            if target is not None:
                target.click()
            return self

        def perform(self):
            pass

    original_actions = mid_clicker.ActionChains
    mid_clicker.ActionChains = DummyActions
    original_send_arrow = mid_clicker.send_arrow_down_native
    mid_clicker.send_arrow_down_native = fake_send_arrow_down_native

    driver = MagicMock()
    driver.find_element.return_value = cell1
    driver.switch_to = switch

    with caplog.at_level(logging.INFO, logger=mid_clicker.MODULE_NAME):
        logger = logging.getLogger(mid_clicker.MODULE_NAME)
        logger.addHandler(caplog.handler)
        try:
            mid_clicker.click_codes_by_arrow(driver, delay=0)
        finally:
            logger.removeHandler(caplog.handler)
            mid_clicker.ActionChains = original_actions
            mid_clicker.send_arrow_down_native = original_send_arrow

    assert cell1.click.called
    assert cell2.click.called
    assert cell3.click.called
    assert cell4.click.called
    summary_found = any("총 클릭" in rec.getMessage() for rec in caplog.records)
    assert summary_found


def test_click_codes_by_loop_iterates_rows(caplog):
    driver = MagicMock()
    driver.find_elements.return_value = [MagicMock() for _ in range(5)]

    cells = [MagicMock() for _ in range(3)]
    for idx, cell in enumerate(cells):
        cell.text = str(idx)

    base = (
        "mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm"
        ".form.div2.form.gdList.body"
    )

    def find_element_side_effect(by, value):
        row_index = int(value.split("gridrow_")[1].split(".")[0])
        return cells[row_index]

    driver.find_element.side_effect = find_element_side_effect

    with caplog.at_level(logging.INFO, logger=mid_clicker.MODULE_NAME):
        logger = logging.getLogger(mid_clicker.MODULE_NAME)
        logger.addHandler(caplog.handler)
        try:
            mid_clicker.click_codes_by_loop(driver, row_limit=3)
        finally:
            logger.removeHandler(caplog.handler)

    for cell in cells:
        assert cell.click.called
    row_log_found = any("순회 대상: 3" in rec.getMessage() for rec in caplog.records)
    assert row_log_found


def test_scroll_loop_click_stops_on_missing(caplog):
    driver = MagicMock()
    cells = [MagicMock(), MagicMock()]
    driver.find_element.side_effect = [cells[0], cells[1], NoSuchElementException()]
    driver.execute_script = MagicMock()

    with caplog.at_level(logging.INFO, logger=mid_clicker.MODULE_NAME):
        logger = logging.getLogger(mid_clicker.MODULE_NAME)
        logger.addHandler(caplog.handler)
        try:
            mid_clicker.scroll_loop_click(driver, max_attempts=5)
        finally:
            logger.removeHandler(caplog.handler)

    assert cells[0].click.called
    assert cells[1].click.called
    assert driver.execute_script.call_count == 2
    assert any("셀 없음" in rec.getMessage() for rec in caplog.records)


def test_grid_scroll_click_loop_basic(caplog):
    driver = MagicMock()
    cells = [MagicMock(), MagicMock()]
    driver.find_element.side_effect = [cells[0], cells[1], NoSuchElementException()]
    driver.execute_script = MagicMock()

    with caplog.at_level(logging.INFO, logger=mid_clicker.MODULE_NAME):
        logger = logging.getLogger(mid_clicker.MODULE_NAME)
        logger.addHandler(caplog.handler)
        try:
            mid_clicker.grid_scroll_click_loop(
                driver,
                "prefix_",
                "_suffix",
                max_rows=5,
            )
        finally:
            logger.removeHandler(caplog.handler)

    assert cells[0].click.called
    assert cells[1].click.called
    assert driver.execute_script.call_count == 2
    assert any("루프 종료" in rec.getMessage() for rec in caplog.records)


def test_grid_click_with_scroll_basic(caplog):
    driver = MagicMock()
    cells = [MagicMock() for _ in range(5)]
    scroll_btn = MagicMock()
    driver.find_element.side_effect = [
        cells[0],
        cells[1],
        cells[2],
        cells[3],
        cells[4],
        scroll_btn,
    ]

    with caplog.at_level(logging.INFO, logger=mid_clicker.MODULE_NAME):
        logger = logging.getLogger(mid_clicker.MODULE_NAME)
        logger.addHandler(caplog.handler)
        try:
            mid_clicker.grid_click_with_scroll(driver, max_rows=5)
        finally:
            logger.removeHandler(caplog.handler)

    for cell in cells:
        assert cell.click.called
    assert scroll_btn.click.call_count == 1
    assert any("루프 종료" in rec.getMessage() for rec in caplog.records)


def test_grid_click_with_scroll_after_4_basic(capsys):
    driver = MagicMock()
    cells = [MagicMock() for _ in range(5)]
    scroll_btn = MagicMock()

    driver.find_element.side_effect = [
        cells[0],
        cells[1],
        cells[2],
        cells[3],
        cells[4],
        scroll_btn,
    ]

    mid_clicker.grid_click_with_scroll_after_4(driver, max_rows=5)

    for cell in cells:
        assert cell.click.called
    assert scroll_btn.click.call_count == 1
    captured = capsys.readouterr().out
    assert "루프 종료" in captured


def test_grid_click_with_scroll_from_20_basic(capsys, tmp_path):
    driver = MagicMock()
    cells = [MagicMock() for _ in range(21)]
    for idx, cell in enumerate(cells):
        cell.text = str(idx)
        cell.get_attribute.return_value = f"cell_{idx}"

    grid_elem = MagicMock()
    scroll_btn1 = MagicMock()
    scroll_btn2 = MagicMock()

    def find_element_side_effect(by, value):
        if by == mid_clicker.By.ID and value.endswith("gdList.body"):
            return grid_elem
        if by == mid_clicker.By.ID and value.endswith("gridrow_0.cell_0_0"):
            return cells[0]
        if by == mid_clicker.By.XPATH:
            find_element_side_effect.calls += 1
            return scroll_btn1 if find_element_side_effect.calls == 1 else scroll_btn2
        raise AssertionError("Unexpected locator")

    find_element_side_effect.calls = 0
    driver.find_element.side_effect = find_element_side_effect

    class DummySwitch:
        def __init__(self, elems):
            self.elems = elems
            self.idx = 0

        @property
        def active_element(self):
            return self.elems[self.idx]

        def next(self):
            if self.idx < len(self.elems) - 1:
                self.idx += 1

    switch = DummySwitch(cells)
    driver.switch_to = switch

    def fake_send_arrow_down_native(_driver):
        switch.next()

    class DummyActions:
        def __init__(self, driver):
            self.driver = driver
            self.element = None

        def move_to_element(self, element):
            self.element = element
            return self

        def perform(self):
            pass

    original_actions = mid_clicker.ActionChains
    original_arrow = mid_clicker.send_arrow_down_native
    original_home = mid_clicker.send_home_native
    mid_clicker.ActionChains = DummyActions
    mid_clicker.send_arrow_down_native = fake_send_arrow_down_native
    mid_clicker.send_home_native = lambda d: None

    log_file = tmp_path / "log.txt"
    try:
        mid_clicker.grid_click_with_scroll_from_20(
            driver,
            max_rows=21,
            log_path=str(log_file),
        )
    finally:
        mid_clicker.ActionChains = original_actions
        mid_clicker.send_arrow_down_native = original_arrow
        mid_clicker.send_home_native = original_home

    for cell in cells:
        assert cell.click.called
    assert scroll_btn1.click.called
    assert scroll_btn2.click.called
    captured = capsys.readouterr().out
    assert "루프 종료" in captured
    assert log_file.is_file()
