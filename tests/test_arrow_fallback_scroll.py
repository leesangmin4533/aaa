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
    next_cell = MagicMock()
    next_cell.text = "002"

    # calls: start_cell, text cell
    driver.find_element.side_effect = [first_cell, next_cell]
    driver.execute_script.side_effect = [None, "cell_0_0", "cell_1_0", None]

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
    assert "찾은 셀 ID" in contents
    assert "완료" in contents
    assert driver.execute_script.call_args_list[0][0][0] == "arguments[0].focus();"


def test_arrow_fallback_scroll_retries_on_no_move(tmp_path):
    log_file = tmp_path / "retry_log.txt"

    driver = MagicMock()
    first_cell = MagicMock()
    first_cell.text = "001"

    # only the initial cell is needed; loop will break before next search
    driver.find_element.side_effect = [first_cell]
    driver.execute_script.side_effect = [None, "cell_0_0", "cell_0_0", "cell_0_0"]

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
        afs.scroll_with_arrow_fallback_loop(driver, max_steps=1, log_path=str(log_file))
    finally:
        afs.ActionChains = original_actions

    with open(log_file, "r", encoding="utf-8") as f:
        contents = f.read()

    assert any("이동 실패" in line for line in contents.splitlines())
    assert len(send_calls) == 2
