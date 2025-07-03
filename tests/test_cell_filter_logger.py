from unittest.mock import MagicMock
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.sales_analysis import cell_filter_logger as cfl


def test_click_cells_log_filter_logs_filter(caplog):
    cells = [MagicMock(), MagicMock(), MagicMock()]
    cells[0].text = "abc"
    cells[1].text = "filter"
    cells[2].text = "xyz"

    for c in cells:
        c.click = MagicMock()

    side_effects = cells + [Exception("stop")]

    def fake_find(by, value):
        result = side_effects.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    driver = MagicMock()
    driver.find_element.side_effect = fake_find

    with caplog.at_level(logging.INFO, logger=cfl.MODULE_NAME):
        logger = logging.getLogger(cfl.MODULE_NAME)
        logger.addHandler(caplog.handler)
        try:
            cfl.click_cells_log_filter(driver, "filter", max_cells=3)
        finally:
            logger.removeHandler(caplog.handler)

    assert cells[0].click.called
    assert cells[1].click.called
    assert cells[2].click.called
    assert any("필터 'filter' 발견" in rec.getMessage() for rec in caplog.records)
