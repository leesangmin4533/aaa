import importlib.util
import pathlib
from unittest.mock import Mock

_spec = importlib.util.spec_from_file_location(
    "js_util", pathlib.Path(__file__).resolve().parents[1] / "utils" / "js_util.py"
)
js_util = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(js_util)


def test_load_collect_past7days_reads_script(tmp_path):
    js_file = tmp_path / "auto_collect_past_7days.js"
    js_file.write_text("console.log('hi');", encoding="utf-8")

    driver = Mock()
    js_util.load_collect_past7days(driver, scripts_dir=tmp_path)

    driver.execute_script.assert_called_once_with("console.log('hi');")


def test_execute_collect_past7days_calls_async():
    driver = Mock()
    js_util.execute_collect_past7days(driver)

    assert driver.execute_async_script.call_count == 1
    arg = driver.execute_async_script.call_args[0][0]
    assert "collectPast7Days()" in arg
