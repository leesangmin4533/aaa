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
    driver.execute_script.side_effect = ["cell_0_0", "cell_1_0"]

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
