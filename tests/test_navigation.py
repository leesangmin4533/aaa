import importlib.util
import pathlib
import sys
import types
from unittest.mock import Mock, patch

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
    "navigation",
    pathlib.Path(__file__).resolve().parents[1] / "analysis" / "navigation.py",
)
navigation = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(navigation)


def test_navigate_success():
    driver = Mock()
    element = object()
    driver.execute_script.side_effect = [element, None, element, None]

    with patch.object(navigation.time, "sleep"), patch.object(navigation, "create_logger", return_value=lambda *a: None):
        assert navigation.navigate_to_category_mix_ratio(driver) is True


def test_navigate_failure():
    driver = Mock()
    element = object()
    responses = [element, None] + [None] * 10

    def _side_effect(*args, **kwargs):
        return responses.pop(0)

    driver.execute_script.side_effect = _side_effect

    with patch.object(navigation.time, "sleep"), patch.object(navigation, "create_logger", return_value=lambda *a: None):
        assert navigation.navigate_to_category_mix_ratio(driver) is False
