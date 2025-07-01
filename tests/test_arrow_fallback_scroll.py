import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.sales_analysis.arrow_fallback_scroll as afs


def test_arrow_fallback_scroll_logs(tmp_path):
    log_file = tmp_path / "arrow_log.txt"

    driver = MagicMock()
    first_cell = MagicMock()
    first_cell.text = "001"
    row_elem = MagicMock()
    row_elem.text = "row text"
    next_cell = MagicMock()
    next_cell.text = "002"

    # start cell, text cell, row element
    driver.find_element.side_effect = [first_cell, next_cell, row_elem]
    driver.execute_script.side_effect = [
        None,  # focus first
        "gridrow_0.cell_0_0",  # initial active id
        "gridrow_1.cell_1_0",  # after first ArrowDown
        "gridrow_1.cell_1_0",  # find_cell_under_mainframe
        None,  # focus after click
        "gridrow_2.cell_2_0",  # next cell after ArrowDown
    ]

    class DummyActions:
        def __init__(self, driver):
            pass

        def move_to_element(self, element):
            return self

        def click(self, element=None):
            return self

        def send_keys(self, *args):
            return self

        def perform(self):
            pass

    original_actions = afs.ActionChains
    afs.ActionChains = DummyActions
    try:
        afs.scroll_with_arrow_fallback_loop(
            driver, max_steps=1, log_path=str(log_file)
        )
    finally:
        afs.ActionChains = original_actions

    with open(log_file, "r", encoding="utf-8") as f:
        contents = f.read()

    assert "ArrowDown" in contents
    assert "현재 셀 ID" in contents
    assert "완료" in contents
    assert driver.execute_script.call_args_list[0][0][0] == "arguments[0].focus();"


def test_arrow_fallback_scroll_forces_move_after_three_same(tmp_path):
    log_file = tmp_path / "retry_log.txt"

    driver = MagicMock()
    cell = MagicMock()
    cell.text = "001"
    driver.find_element.return_value = cell
    driver.execute_script.return_value = "gridrow_0.cell_0_0"

    send_calls = []

    class DummyActions:
        def __init__(self, driver):
            pass

        def move_to_element(self, element):
            return self

        def click(self, element=None):
            return self

        def send_keys(self, *args):
            send_calls.append(args)
            return self

        def perform(self):
            pass

    original_actions = afs.ActionChains
    afs.ActionChains = DummyActions
    try:
        afs.scroll_with_arrow_fallback_loop(driver, max_steps=3, log_path=str(log_file))
    finally:
        afs.ActionChains = original_actions

    with open(log_file, "r", encoding="utf-8") as f:
        contents = f.read()

    assert "반복 중단" in contents
    assert len(send_calls) == 5
