import os
from unittest.mock import MagicMock
from pathlib import Path
from selenium.common.exceptions import NoSuchElementException
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.sales_analysis.grid_click_logger import scroll_and_click_loop


def test_scroll_and_click_loop_logs(tmp_path):
    log_file = tmp_path / "test_log.txt"

    driver = MagicMock()
    cells = [MagicMock(), MagicMock()]
    cells[0].text = "001"
    cells[1].text = "002"
    driver.find_element.side_effect = [cells[0], cells[1], NoSuchElementException()]
    driver.execute_script = MagicMock()

    scroll_and_click_loop(driver, max_cells=5, log_path=str(log_file))

    assert cells[0].click.called
    assert cells[1].click.called
    with open(log_file, "r", encoding="utf-8") as f:
        log_contents = f.read()
    assert "클릭 완료" in log_contents
    assert "루프 종료" in log_contents
