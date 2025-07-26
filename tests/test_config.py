import importlib.util
import pathlib

def test_default_script_name():
    spec = importlib.util.spec_from_file_location(
        "automation.config", pathlib.Path(__file__).resolve().parents[1] / "automation" / "config.py"
    )
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    assert config.DEFAULT_SCRIPT == "nexacro_automation_library.js"
    assert config.config["scripts"]["default"] == "nexacro_automation_library.js"

