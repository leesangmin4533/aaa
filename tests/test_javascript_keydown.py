import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.common.login import run_step


def test_javascript_keydown_executes_script():
    driver = MagicMock()
    step = {
        "action": "javascript_keydown",
        "target_id": "cell_0",
        "key": "ArrowDown",
    }
    run_step(driver, step, {}, {})

    driver.execute_script.assert_called_once()
    args, kwargs = driver.execute_script.call_args
    assert "KeyboardEvent" in args[0]
    assert args[1] == "cell_0"
    assert args[2] == "ArrowDown"
    assert args[3] == 40
