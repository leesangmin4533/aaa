import os
from unittest.mock import MagicMock
from pathlib import Path
from selenium.common.exceptions import NoSuchElementException
import sys
import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.sales_analysis.grid_click_logger as grid_click_logger
from modules.sales_analysis.grid_click_logger import scroll_and_click_loop


def test_scroll_and_click_loop_logs(tmp_path):
    log_file = tmp_path / "test_log.txt"

    driver = MagicMock()
    cells = [MagicMock(), MagicMock()]
    cells[0].text = "001"
    cells[1].text = "002"

    side_effects = [
        cells[0],  # first cell
        cells[1],  # next cell after arrow
        cells[1],  # second iteration current cell
        NoSuchElementException(),  # missing next cell
        NoSuchElementException(),  # third iteration first cell missing -> break
    ]

    def fake_find(*args, **kwargs):
        result = side_effects.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    driver.find_element.side_effect = fake_find
    driver.execute_script = MagicMock(return_value="cell_0_0")

    scroll_and_click_loop(driver, max_cells=5, log_path=str(log_file))

    assert cells[0].click.called
    assert cells[0].send_keys.called
    assert cells[1].click.called
    assert cells[1].send_keys.called
    with open(log_file, "r", encoding="utf-8") as f:
        log_contents = f.read()
    assert "클릭 시도" in log_contents
    assert "순회 종료" in log_contents


def test_scroll_and_click_loop_flush_on_exception(tmp_path):
    log_file = tmp_path / "test_log.txt"

    driver = MagicMock()

    class FailingActions:
        def __init__(self, _driver):
            raise RuntimeError("fail")

    original_actions = grid_click_logger.ActionChains
    grid_click_logger.ActionChains = FailingActions
    try:
        with pytest.raises(RuntimeError):
            scroll_and_click_loop(driver, log_path=str(log_file))
    finally:
        grid_click_logger.ActionChains = original_actions

    with open(log_file, "r", encoding="utf-8") as f:
        contents = f.read()
    assert "실행: 셀 순회 시작" in contents
