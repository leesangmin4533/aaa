from unittest.mock import MagicMock
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.sales_analysis.row_click_by_arrow as rca


def test_row_click_by_arrow_clicks_numeric():
    start_cell = MagicMock()
    start_cell.text = "001"
    start_cell.get_attribute.return_value = "prefix.gridrow_0.cell_0_0"

    text_cell1 = MagicMock()
    text_cell1.text = "001"
    text_cell1.get_attribute.return_value = "ignored"
    real_cell1 = MagicMock()
    real_cell1.get_attribute.return_value = "prefix.gridrow_1.cell_1_0"

    text_cell2 = MagicMock()
    text_cell2.text = "abc"
    text_cell2.get_attribute.return_value = "ignored"
    real_cell2 = MagicMock()
    real_cell2.get_attribute.return_value = "prefix.gridrow_2.cell_2_0"

    # driver.find_element calls in order:
    # 0 start cell
    # 1 text cell for row 0
    # 2 real cell for row 0
    # 3 text cell for row 1
    # 4 real cell for row 1
    driver = MagicMock()
    driver.find_element.side_effect = [
        start_cell,
        text_cell1,
        real_cell1,
        text_cell2,
        real_cell2,
    ]

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

    switch = DummySwitch([start_cell, real_cell1, real_cell2])
    driver.switch_to = switch
    driver.execute_script = MagicMock()

    moves = []

    class DummyActions:
        def __init__(self, _driver):
            pass

        def move_to_element(self, elem):
            self.elem = elem
            return self

        def click(self, element=None):
            (element or self.elem).click()
            return self

        def send_keys(self, *args):
            moves.append(args)
            switch.next()
            return self

        def perform(self):
            pass

    original_actions = rca.ActionChains
    rca.ActionChains = DummyActions
    try:
        rca.row_click_by_arrow(
            driver,
            start_cell_id="prefix.gridrow_0.cell_0_0",
            max_steps=2,
            delay=0,
        )
    finally:
        rca.ActionChains = original_actions

    assert real_cell1.click.called
    assert not real_cell2.click.called
    assert len(moves) >= 2
