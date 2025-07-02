import sys
import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.common import login as login_module


def test_run_login_raises_on_step_failure(tmp_path, monkeypatch):
    config_file = tmp_path / "conf.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump({"steps": [{"action": "dummy"}]}, f)

    driver = MagicMock()

    def fail_step(driver, step, elements, env):
        raise RuntimeError("fail")

    monkeypatch.setattr(login_module, "run_step", fail_step)
    monkeypatch.setattr(login_module, "load_env", lambda: {"LOGIN_ID": "id", "LOGIN_PW": "pw"})

    with pytest.raises(RuntimeError):
        login_module.run_login(driver, config_path=str(config_file))

