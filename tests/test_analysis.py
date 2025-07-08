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
support_pkg = types.ModuleType("selenium.webdriver.support")
ui_module = types.ModuleType("selenium.webdriver.support.ui")
ec_module = types.ModuleType("selenium.webdriver.support.expected_conditions")
common_by_pkg = types.ModuleType("selenium.webdriver.common")
by_module = types.ModuleType("selenium.webdriver.common.by")
def visibility_of_element_located(locator):
    def _inner(driver):
        return None
    return _inner
ec_module.visibility_of_element_located = visibility_of_element_located
class WebDriverWait: ...
ui_module.WebDriverWait = WebDriverWait
class By:
    XPATH = "xpath"
by_module.By = By
class WebDriver: ...
webdriver_module.WebDriver = WebDriver
remote_pkg.webdriver = webdriver_module
webdriver_pkg.remote = remote_pkg
support_pkg.ui = ui_module
webdriver_pkg.support = support_pkg
support_pkg.expected_conditions = ec_module
common_by_pkg.by = by_module
common_pkg = types.ModuleType("selenium.common")
exceptions_module = types.ModuleType("selenium.common.exceptions")
class WebDriverException(Exception):
    pass
exceptions_module.WebDriverException = WebDriverException
common_pkg.exceptions = exceptions_module
selenium_pkg.webdriver = webdriver_pkg
selenium_pkg.common = common_pkg
sys.modules.setdefault("selenium", selenium_pkg)
sys.modules.setdefault("selenium.webdriver", webdriver_pkg)
sys.modules.setdefault("selenium.webdriver.remote", remote_pkg)
sys.modules.setdefault("selenium.webdriver.remote.webdriver", webdriver_module)
sys.modules.setdefault("selenium.webdriver.support", support_pkg)
sys.modules.setdefault("selenium.webdriver.support.ui", ui_module)
sys.modules.setdefault("selenium.webdriver.support.expected_conditions", ec_module)
sys.modules.setdefault("selenium.webdriver.common", common_by_pkg)
sys.modules.setdefault("selenium.webdriver.common.by", by_module)
sys.modules.setdefault("selenium.common", common_pkg)
sys.modules.setdefault("selenium.common.exceptions", exceptions_module)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
_spec = importlib.util.spec_from_file_location(
    "analysis", pathlib.Path(__file__).resolve().parents[1] / "analysis" / "__init__.py"
)
analysis = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(analysis)


def test_click_all_product_codes_executes_js():
    driver = Mock()
    analysis.click_all_product_codes(driver)

    driver.execute_script.assert_called_once()
