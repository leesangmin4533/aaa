from unittest.mock import Mock, patch
import importlib.util
import pathlib
import sys
import types

# Create minimal fake selenium package
selenium_pkg = types.ModuleType("selenium")
webdriver_pkg = types.ModuleType("selenium.webdriver")
remote_pkg = types.ModuleType("selenium.webdriver.remote")
webdriver_module = types.ModuleType("selenium.webdriver.remote.webdriver")
class WebDriver: ...
webdriver_module.WebDriver = WebDriver
remote_pkg.webdriver = webdriver_module
webdriver_pkg.remote = remote_pkg
selenium_pkg.webdriver = webdriver_pkg
sys.modules.setdefault("selenium", selenium_pkg)
sys.modules.setdefault("selenium.webdriver", webdriver_pkg)
sys.modules.setdefault("selenium.webdriver.remote", remote_pkg)
sys.modules.setdefault("selenium.webdriver.remote.webdriver", webdriver_module)

# Load grid_utils without requiring the selenium dependency
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
_spec = importlib.util.spec_from_file_location(
    "grid_utils", pathlib.Path(__file__).resolve().parents[1] / "analysis" / "grid_utils.py"
)
grid_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grid_utils)


def test_get_product_row_texts_basic():
    driver = Mock()
    driver.execute_script.side_effect = [f"text{i}" for i in range(3)]

    result = grid_utils.get_product_row_texts(driver, row=1, col_count=3)

    assert result == ["text0", "text1", "text2"]
    assert driver.execute_script.call_count == 3
    for idx, call in enumerate(driver.execute_script.call_args_list):
        assert call.args[1] == 1
        assert call.args[2] == idx


def fake_time_generator(start: float = 0.0, step: float = 0.1):
    t = start
    def _fake_time():
        nonlocal t
        val = t
        t += step
        return val
    return _fake_time


def test_wait_for_grid_update_success():
    driver = Mock()
    driver.execute_script.side_effect = ["old", "old", "new"]

    fake_time = fake_time_generator()
    with patch.object(grid_utils, "time") as tm:
        tm.time.side_effect = fake_time
        tm.sleep.side_effect = lambda x: None
        assert grid_utils.wait_for_grid_update(driver, "old", timeout=1.0) is True


def test_wait_for_grid_update_timeout():
    driver = Mock()
    driver.execute_script.return_value = "same"

    fake_time = fake_time_generator()
    with patch.object(grid_utils, "time") as tm:
        tm.time.side_effect = fake_time
        tm.sleep.side_effect = lambda x: None
        assert grid_utils.wait_for_grid_update(driver, "same", timeout=1.0) is False


def test_click_all_visible_product_codes_basic():
    driver = Mock()
    driver.execute_script.return_value = ["111", "222"]

    result = grid_utils.click_all_visible_product_codes(driver)

    assert result == 2
    driver.execute_script.assert_called_once()
    assert isinstance(driver.execute_script.call_args.args[0], str)


def test_click_all_visible_product_codes_polling():
    driver = Mock()
    driver.execute_script.side_effect = [[], ["333"]]

    with patch.object(grid_utils.time, "sleep") as sleep_mock:
        result = grid_utils.click_all_visible_product_codes(driver)

    assert result == 1
    assert driver.execute_script.call_count == 2
    sleep_mock.assert_called_once_with(0.5)

