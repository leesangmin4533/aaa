import importlib.util
import pathlib
import sys
import types
from unittest.mock import Mock, patch

# Create minimal fake selenium package
selenium_pkg = types.ModuleType("selenium")
webdriver_pkg = types.ModuleType("selenium.webdriver")
remote_pkg = types.ModuleType("selenium.webdriver.remote")
webdriver_module = types.ModuleType("selenium.webdriver.remote.webdriver")
support_pkg = types.ModuleType("selenium.webdriver.support")
ui_pkg = types.ModuleType("selenium.webdriver.support.ui")
common_pkg = types.ModuleType("selenium.webdriver.common")
action_pkg = types.ModuleType("selenium.webdriver.common.action_chains")
keys_pkg = types.ModuleType("selenium.webdriver.common.keys")
by_pkg = types.ModuleType("selenium.webdriver.common.by")

class WebDriver: ...
webdriver_module.WebDriver = WebDriver

class WebDriverWait:
    def __init__(self, driver, timeout):
        pass
    def until(self, method):
        return True
ui_pkg.WebDriverWait = WebDriverWait
support_pkg.ui = ui_pkg

class ActionChains:
    def __init__(self, driver):
        self.driver = driver
    def send_keys(self, key):
        return self
    def perform(self):
        pass
action_pkg.ActionChains = ActionChains

class Keys:
    ENTER = "ENTER"
keys_pkg.Keys = Keys

class By:
    XPATH = "xpath"
by_pkg.By = By

remote_pkg.webdriver = webdriver_module
webdriver_pkg.remote = remote_pkg
selenium_pkg.webdriver = webdriver_pkg
selenium_pkg.webdriver.support = support_pkg
selenium_pkg.webdriver.support.ui = ui_pkg
selenium_pkg.webdriver.common = common_pkg
selenium_pkg.webdriver.common.action_chains = action_pkg
selenium_pkg.webdriver.common.keys = keys_pkg
selenium_pkg.webdriver.common.by = by_pkg

sys.modules.setdefault("selenium", selenium_pkg)
sys.modules.setdefault("selenium.webdriver", webdriver_pkg)
sys.modules.setdefault("selenium.webdriver.remote", remote_pkg)
sys.modules.setdefault("selenium.webdriver.remote.webdriver", webdriver_module)
sys.modules.setdefault("selenium.webdriver.support", support_pkg)
sys.modules.setdefault("selenium.webdriver.support.ui", ui_pkg)
sys.modules.setdefault("selenium.webdriver.common", common_pkg)
sys.modules.setdefault("selenium.webdriver.common.action_chains", action_pkg)
sys.modules.setdefault("selenium.webdriver.common.keys", keys_pkg)
sys.modules.setdefault("selenium.webdriver.common.by", by_pkg)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

_spec = importlib.util.spec_from_file_location(
    "utils.popup_util",
    pathlib.Path(__file__).resolve().parents[1] / "utils" / "popup_util.py",
)
popup_util = importlib.util.module_from_spec(_spec)
utils_pkg = types.ModuleType("utils")
utils_pkg.__path__ = [str(pathlib.Path(__file__).resolve().parents[1] / "utils")]
sys.modules["utils"] = utils_pkg
_spec.loader.exec_module(popup_util)


def test_ensure_focus_popup_closed_closes_until_gone():
    driver = Mock()
    popup = Mock()
    popup.is_displayed.side_effect = [True]
    driver.find_element.side_effect = [popup, Exception("missing"), Exception("missing")]
    with patch.object(popup_util.time, "sleep"):
        popup_util.ensure_focus_popup_closed(driver, timeout=1, stable_time=0.1)

    assert driver.find_element.call_count >= 2
