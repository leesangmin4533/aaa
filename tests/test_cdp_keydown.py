import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.common.login import run_step


def test_cdp_keydown_executes_cdp():
    driver = MagicMock()
    step = {
        "action": "cdp_keydown",
        "key": "ArrowDown",
        "windowsVirtualKeyCode": 40,
    }
    run_step(driver, step, {}, {})

    assert driver.execute_cdp_cmd.call_count == 2
    args_down, _ = driver.execute_cdp_cmd.call_args_list[0]
    assert args_down[0] == "Input.dispatchKeyEvent"
    assert args_down[1]["type"] == "keyDown"
    assert args_down[1]["key"] == "ArrowDown"
