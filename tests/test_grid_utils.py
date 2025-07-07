from unittest.mock import Mock
import importlib.util
import pathlib
import sys
import types

# minimal fake selenium package
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

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
_spec = importlib.util.spec_from_file_location(
    "grid_utils", pathlib.Path(__file__).resolve().parents[1] / "analysis" / "grid_utils.py"
)
grid_utils = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grid_utils)


def test_find_text_cell_by_code_found():
    driver = Mock()
    driver.execute_script.return_value = "el"

    result = grid_utils.find_text_cell_by_code(driver, "001")

    assert result == "el"
    driver.execute_script.assert_called_once()


def test_find_text_cell_by_code_not_found():
    driver = Mock()
    driver.execute_script.return_value = None

    result = grid_utils.find_text_cell_by_code(driver, "001")

    assert result is None


def test_find_clickable_cell_by_code_success():
    driver = Mock()
    text_el = object()
    driver.execute_script.side_effect = [text_el, "cid", "click_el"]

    result = grid_utils.find_clickable_cell_by_code(driver, "001")

    assert result == "click_el"
    assert driver.execute_script.call_count == 3


def test_find_clickable_cell_by_code_no_text():
    driver = Mock()
    driver.execute_script.return_value = None

    result = grid_utils.find_clickable_cell_by_code(driver, "001")

    assert result is None


def test_find_clickable_cell_by_code_no_click_el():
    driver = Mock()
    text_el = object()
    driver.execute_script.side_effect = [text_el, "cid", None]

    result = grid_utils.find_clickable_cell_by_code(driver, "001")

    assert result is None
