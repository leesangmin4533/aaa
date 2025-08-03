import importlib.util
import pathlib
import sys

def test_default_script_name():
    root = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location(
        "automation.config", root / "automation" / "config.py"
    )
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    assert config.DEFAULT_SCRIPT == "nexacro_automation_library.js"
    assert config.config["scripts"]["default"] == "nexacro_automation_library.js"

