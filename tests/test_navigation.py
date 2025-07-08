import importlib.util
import pathlib
import sys
import types
from unittest.mock import Mock, patch, call

# minimal fake selenium package
selenium_pkg = types.ModuleType("selenium")
webdriver_pkg = types.ModuleType("selenium.webdriver")
remote_pkg = types.ModuleType("selenium.webdriver.remote")
webdriver_module = types.ModuleType("selenium.webdriver.remote.webdriver")
support_pkg = types.ModuleType("selenium.webdriver.support")
ui_module = types.ModuleType("selenium.webdriver.support.ui")
class WebDriverWait: ...
ui_module.WebDriverWait = WebDriverWait

class WebDriver:
    ...

webdriver_module.WebDriver = WebDriver
remote_pkg.webdriver = webdriver_module
webdriver_pkg.remote = remote_pkg
support_pkg.ui = ui_module
webdriver_pkg.support = support_pkg
selenium_pkg.webdriver = webdriver_pkg

sys.modules.setdefault("selenium", selenium_pkg)
sys.modules.setdefault("selenium.webdriver", webdriver_pkg)
sys.modules.setdefault("selenium.webdriver.remote", remote_pkg)
sys.modules.setdefault("selenium.webdriver.remote.webdriver", webdriver_module)
sys.modules.setdefault("selenium.webdriver.support", support_pkg)
sys.modules.setdefault("selenium.webdriver.support.ui", ui_module)

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
_spec = importlib.util.spec_from_file_location(
    "navigation",
    pathlib.Path(__file__).resolve().parents[1] / "analysis" / "navigation.py",
)
navigation = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(navigation)


def test_click_menu_by_text_success():
    driver = Mock()
    elem = object()
    driver.execute_script.side_effect = [elem, None]

    wait_mock = Mock()
    wait_mock.until.side_effect = lambda func: func(driver)

    with patch.object(navigation, "WebDriverWait", return_value=wait_mock):
        result = navigation.click_menu_by_text(driver, "메뉴")

    assert result is True
    driver.execute_script.assert_called_with("arguments[0].click()", elem)


def test_click_menu_by_text_failure():
    driver = Mock()
    wait_mock = Mock()
    wait_mock.until.side_effect = Exception("no")

    with patch.object(navigation, "WebDriverWait", return_value=wait_mock):
        result = navigation.click_menu_by_text(driver, "메뉴")

    assert result is False


def test_go_to_mix_ratio_screen():
    driver = Mock()
    with patch.object(navigation, "click_menu_by_text", side_effect=[True, True]) as m:
        assert navigation.go_to_mix_ratio_screen(driver) is True
        m.assert_has_calls(
            [
                call(driver, "매출분석"),
                call(driver, "중분류별 매출 구성비"),
            ]
        )

    with patch.object(navigation, "click_menu_by_text", side_effect=[True, False]) as m:
        assert navigation.go_to_mix_ratio_screen(driver) is False
        m.assert_called_with(driver, "중분류별 매출 구성비")
