import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.common.popup_utils import close_popups, POPUP_CLOSE_SCRIPT


class DummyDriver:
    def __init__(self):
        self.execute_script = Mock(return_value={"detected": False})


def test_close_popups_executes_script():
    driver = DummyDriver()
    result = close_popups(driver)
    driver.execute_script.assert_called_once_with(POPUP_CLOSE_SCRIPT)
    assert result == {"detected": False}

