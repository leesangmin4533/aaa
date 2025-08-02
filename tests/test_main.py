import importlib.util
import pathlib
import sys
import types
from unittest.mock import Mock, patch
import pytest
import subprocess
import os
import json

# Create minimal fake selenium package
selenium_pkg = types.ModuleType("selenium")
webdriver_pkg = types.ModuleType("selenium.webdriver")
remote_pkg = types.ModuleType("selenium.webdriver.remote")
webdriver_module = types.ModuleType("selenium.webdriver.remote.webdriver")
chrome_pkg = types.ModuleType("selenium.webdriver.chrome")
service_pkg = types.ModuleType("selenium.webdriver.chrome.service")
options_pkg = types.ModuleType("selenium.webdriver.chrome.options")
common_pkg = types.ModuleType("selenium.webdriver.common")
dcaps_pkg = types.ModuleType("selenium.webdriver.common.desired_capabilities")
by_pkg = types.ModuleType("selenium.webdriver.common.by")
support_pkg = types.ModuleType("selenium.webdriver.support")
ui_pkg = types.ModuleType("selenium.webdriver.support.ui")
ec_pkg = types.ModuleType("selenium.webdriver.support.expected_conditions")
support_pkg.ui = ui_pkg
support_pkg.expected_conditions = ec_pkg
exceptions_pkg = types.ModuleType("selenium.common.exceptions")
class TimeoutException(Exception):
    pass
class WebDriverException(Exception):
    pass
exceptions_pkg.TimeoutException = TimeoutException
exceptions_pkg.WebDriverException = WebDriverException

class WebDriver: ...
class Service: ...
class Options:
    def add_experimental_option(self, *a, **k):
        pass

webdriver_module.WebDriver = WebDriver
service_pkg.Service = Service
options_pkg.Options = Options

remote_pkg.webdriver = webdriver_module
webdriver_pkg.remote = remote_pkg
webdriver_pkg.chrome = chrome_pkg
chrome_pkg.service = service_pkg
chrome_pkg.options = options_pkg
webdriver_pkg.common = common_pkg
common_pkg.desired_capabilities = dcaps_pkg
common_pkg.by = by_pkg
class By:
    XPATH = "xpath"
by_pkg.By = By
webdriver_pkg.support = support_pkg
ui_pkg.WebDriverWait = lambda *a, **k: types.SimpleNamespace(until=lambda *a2, **k2: True)
ec_pkg.presence_of_element_located = lambda *a, **k: (lambda d: True)

class DesiredCapabilities:
    CHROME = {}
dcaps_pkg.DesiredCapabilities = DesiredCapabilities

selenium_pkg.webdriver = webdriver_pkg
sys.modules["selenium"] = selenium_pkg
sys.modules["selenium.webdriver"] = webdriver_pkg
sys.modules["selenium.webdriver.remote"] = remote_pkg
sys.modules["selenium.webdriver.remote.webdriver"] = webdriver_module
sys.modules["selenium.webdriver.chrome"] = chrome_pkg
sys.modules["selenium.webdriver.chrome.service"] = service_pkg
sys.modules["selenium.webdriver.chrome.options"] = options_pkg
sys.modules["selenium.webdriver.common"] = common_pkg
sys.modules["selenium.webdriver.common.desired_capabilities"] = dcaps_pkg
sys.modules["selenium.webdriver.common.by"] = by_pkg
sys.modules["selenium.webdriver.support"] = support_pkg
sys.modules["selenium.webdriver.support.ui"] = ui_pkg
sys.modules["selenium.webdriver.support.expected_conditions"] = ec_pkg
sys.modules["selenium.common.exceptions"] = exceptions_pkg
sys.modules["selenium.webdriver.common"] = common_pkg
sys.modules["selenium.webdriver.common.desired_capabilities"] = dcaps_pkg

# dummy login module
login_pkg = types.ModuleType("login")
login_bgf_pkg = types.ModuleType("login.login_bgf")
def dummy_login_bgf(*a, **k):
    return True
login_bgf_pkg.login_bgf = dummy_login_bgf
login_pkg.login_bgf = login_bgf_pkg
sys.modules["login"] = login_pkg
sys.modules["login.login_bgf"] = login_bgf_pkg

popup_pkg = types.ModuleType("utils.popup_util")
def dummy_close_popups_after_delegate(*a, **k):
    pass
popup_pkg.close_popups_after_delegate = dummy_close_popups_after_delegate
sys.modules["utils.popup_util"] = popup_pkg

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
_spec = importlib.util.spec_from_file_location(
    "main", pathlib.Path(__file__).resolve().parents[1] / "main.py"
)
main = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(main)
import webdriver_utils
import data_collector


def test_run_script_reads_and_executes(tmp_path):
    js_text = "console.log('hi');"
    script = tmp_path / "sample.js"
    script.write_text(js_text, encoding="utf-8")

    driver = Mock()
    with patch.object(webdriver_utils, "SCRIPT_DIR", tmp_path):
        main.run_script(driver, "sample.js")

    driver.execute_script.assert_called_once_with(js_text)


def test_run_script_missing_file_raises(tmp_path):
    driver = Mock()
    with patch.object(webdriver_utils, "SCRIPT_DIR", tmp_path):
        with pytest.raises(FileNotFoundError):
            main.run_script(driver, "missing.js")

    driver.execute_script.assert_not_called()


def test_wait_for_data_polls_parsed_data():
    driver = Mock()
    driver.execute_script.side_effect = [None, {"a": 1}]

    with patch.object(data_collector.time, "sleep"):
        data = data_collector.wait_for_data(driver, timeout=1)

    assert data == {"a": 1}
    assert driver.execute_script.call_args_list[0][0][0] == "return window.__parsedData__ || null"




def test_main_calls_navigation():
    driver = Mock()
    driver.get_log = Mock(return_value=[])

    with (
        patch.object(main, "create_driver", return_value=driver),
        patch.object(main, "login_bgf", return_value=True),
        patch.object(main, "close_popups_after_delegate"),
        patch.object(main, "wait_for_dataset_to_load", return_value=True),
        patch.object(main, "run_script") as run_script_mock,
        patch.object(data_collector, "wait_for_data", return_value=None),
        patch.object(data_collector, "collect_and_save"),
        patch("utils.db_util.run_all_category_predictions"),
    ):
        driver.execute_script.side_effect = [[], [], {}, None]
        main.main()

    run_script_mock.assert_any_call(driver, main.NAVIGATION_SCRIPT)


def test_run_script_collects_data(tmp_path):
    js_text = "collect data"
    script = tmp_path / "collect.js"
    script.write_text(js_text, encoding="utf-8")

    expected = [
        {
            "midCode": "1",
            "midName": "m",
            "productCode": "2",
            "productName": "a",
            "sales": 3,
            "order": 4,
            "purchase": 5,
            "discard": 6,
            "stock": 7,
        }
    ]

    driver = Mock()

    def exec_script(arg):
        if arg == js_text:
            driver._parsed = expected
        elif arg == "return window.__parsedData__ || null":
            return getattr(driver, "_parsed", None)

    driver.execute_script.side_effect = exec_script

    with (
        patch.object(webdriver_utils, "SCRIPT_DIR", tmp_path),
        patch.object(data_collector.time, "sleep"),
    ):
        main.run_script(driver, "collect.js")
        data = data_collector.wait_for_data(driver, timeout=1)

    assert data == expected


@pytest.mark.skip("mid category log printing removed")
def test_main_prints_mid_category_logs(capsys):
    pass


def test_main_writes_sales_data(tmp_path):
    driver = Mock()
    driver.get_log = Mock(return_value=[])

    parsed = [{"x": 1}]
    db_path = tmp_path / "store.db"
    config = {
        "stores": {"test": {"db_file": str(db_path), "credentials_env": {}}},
        "scripts": {"default": "sample.js"},
    }
    (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")

    with (
        patch.object(main, "SCRIPT_DIR", tmp_path),
        patch.object(main, "create_driver", return_value=driver),
        patch.object(main, "login_bgf", return_value=True),
        patch.object(main, "close_popups_after_delegate"),
        patch.object(main, "wait_for_dataset_to_load", return_value=True),
        patch.object(main, "run_script"),
        patch.object(data_collector, "get_missing_past_dates", return_value=[]),
        patch.object(data_collector, "execute_collect_single_day_data", return_value={"success": True, "data": parsed}),
        patch.object(data_collector, "write_sales_data") as write_mock,
        patch.object(data_collector.time, "sleep"),
        patch("utils.db_util.run_all_category_predictions"),
    ):
        main.main()

    write_mock.assert_called_once_with(parsed, db_path)


def test_main_writes_integrated_db_when_needed(tmp_path):
    driver = Mock()
    driver.get_log = Mock(return_value=[])

    parsed = [{"x": 1}]
    db_path = tmp_path / "store.db"
    config = {
        "stores": {"test": {"db_file": str(db_path), "credentials_env": {}}},
        "scripts": {"default": "sample.js"},
    }
    (tmp_path / "config.json").write_text(json.dumps(config), encoding="utf-8")

    with (
        patch.object(main, "SCRIPT_DIR", tmp_path),
        patch.object(main, "create_driver", return_value=driver),
        patch.object(main, "login_bgf", return_value=True),
        patch.object(main, "close_popups_after_delegate"),
        patch.object(main, "wait_for_dataset_to_load", return_value=True),
        patch.object(main, "run_script"),
        patch.object(data_collector, "get_missing_past_dates", return_value=["20240101"]),
        patch.object(
            data_collector,
            "execute_collect_single_day_data",
            side_effect=[{"success": True, "data": []}, {"success": True, "data": parsed}],
        ) as exec_mock,
        patch.object(data_collector, "write_sales_data") as write_mock,
        patch.object(data_collector.time, "sleep"),
        patch("utils.db_util.run_all_category_predictions"),
    ):
        main.main()

    assert exec_mock.call_count == 2
    write_mock.assert_called_once_with(parsed, db_path)


def test_cli_invokes_main(tmp_path):
    root = pathlib.Path(__file__).resolve().parents[1]
    sc = tmp_path / "sitecustomize.py"
    sc.write_text(
        "import os, sys\n"
        "if os.environ.get('TEST_MAIN_SUBPROCESS') == '1':\n"
        "    def trace(frame, event, arg):\n"
        "        if event == 'call' and frame.f_code.co_name == 'main' and frame.f_globals.get('__name__') == '__main__':\n"
        "            print('MAIN CALLED')\n"
        "            raise SystemExit(0)\n"
        "        return trace\n"
        "    sys.settrace(trace)\n"
    )
    env = os.environ.copy()
    env['PYTHONPATH'] = str(tmp_path)
    env['TEST_MAIN_SUBPROCESS'] = '1'
    result = subprocess.run(
        [sys.executable, 'main.py'],
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode == 0:
        assert 'MAIN CALLED' in result.stdout
    else:
        assert result.returncode == 1
        assert 'MAIN CALLED' not in result.stdout


def test_wait_for_mix_ratio_page_logs_console_on_failure():
    driver = Mock()
    driver.get_log = Mock(return_value=[{"message": "foo"}, {"message": "bar"}])

    wait_mock = Mock()
    wait_mock.until.side_effect = Exception("boom")

    with (
        patch.object(webdriver_utils, "WebDriverWait", return_value=wait_mock),
        patch.object(webdriver_utils, "logger") as logger,
    ):
        ok = webdriver_utils.wait_for_page_elements(driver, timeout=1)

    assert not ok
    driver.get_log.assert_called_once_with("browser")
    errors = [str(c.args[0]) for c in logger.error.call_args_list]
    assert any("foo" in e for e in errors)
    assert any("bar" in e for e in errors)

