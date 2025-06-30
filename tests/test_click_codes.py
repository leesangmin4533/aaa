import sys
from pathlib import Path
from unittest.mock import MagicMock
from selenium.webdriver.common.keys import Keys
import logging

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.sales_analysis.mid_category_clicker import click_codes_by_arrow


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

    def make_send_keys():
        def _send_keys(key):
            if key == Keys.ARROW_DOWN:
                switch.next()
        return _send_keys

    for c in cells:
        c.send_keys.side_effect = make_send_keys()

    driver = MagicMock()
    driver.find_element.return_value = cell1
    driver.switch_to = switch

    with caplog.at_level(logging.INFO):
        click_codes_by_arrow(driver, delay=0)

    assert cell1.click.called
    assert cell2.click.called
    assert cell3.click.called
    assert cell4.click.called
    summary_found = any("총 클릭" in rec.getMessage() for rec in caplog.records)
    assert summary_found
