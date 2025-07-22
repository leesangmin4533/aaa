import importlib.util
import pathlib
import sys
import types
from datetime import datetime
from unittest.mock import Mock, patch
import pytest
import subprocess
import os

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


def test_run_script_reads_and_executes(tmp_path):
    js_text = "console.log('hi');"
    script = tmp_path / "sample.js"
    script.write_text(js_text, encoding="utf-8")

    driver = Mock()
    with patch.object(main, "SCRIPT_DIR", tmp_path):
        main.run_script(driver, "sample.js")

    driver.execute_script.assert_called_once_with(js_text)


def test_run_script_missing_file_raises(tmp_path):
    driver = Mock()
    with patch.object(main, "SCRIPT_DIR", tmp_path):
        with pytest.raises(FileNotFoundError):
            main.run_script(driver, "missing.js")

    driver.execute_script.assert_not_called()


def test_wait_for_data_polls_parsed_data():
    driver = Mock()
    driver.execute_script.side_effect = [None, {"a": 1}]

    with patch.object(main.time, "sleep"):
        data = main.wait_for_data(driver, timeout=1)

    assert data == {"a": 1}
    assert driver.execute_script.call_args_list[0][0][0] == "return window.__parsedData__ || null"


def test_save_to_txt_writes_to_date_file(tmp_path):
    data = [
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
    out_dir = tmp_path / "code_outputs"
    out_dir.mkdir()
    fname = datetime.now().strftime("%Y%m%d") + ".txt"
    out_file = out_dir / fname

    returned = main.save_to_txt(data, out_file)

    assert returned == out_file
    expected = "\t".join(str(data[0].get(k, "")) for k in main.FIELD_ORDER)
    assert out_file.read_text(encoding="utf-8").strip() == expected


def test_save_to_txt_field_order(tmp_path):
    data = [
        {
            "midCode": "001",
            "midName": "abc-mid",
            "productCode": "123",
            "productName": "abc",
            "sales": 1,
            "order": 2,
            "purchase": 3,
            "discard": 4,
            "stock": 5,
        }
    ]
    out_file = tmp_path / "out.txt"

    main.save_to_txt(data, out_file)

    contents = out_file.read_text(encoding="utf-8").strip().split("\t")
    assert contents == [str(data[0].get(k, "")) for k in main.FIELD_ORDER]


def test_save_to_txt_creates_parent_dir(tmp_path):
    out_file = tmp_path / "nested" / "dir" / "out.txt"
    main.save_to_txt(["a"], out_file)
    assert out_file.exists()


def test_main_calls_navigation():
    driver = Mock()
    driver.get_log = Mock(return_value=[])

    with (
        patch.object(main, "create_driver", return_value=driver),
        patch.object(main, "login_bgf", return_value=True),
        patch.object(main, "close_popups_after_delegate"),
        patch.object(main, "wait_for_mix_ratio_page", return_value=True),
        patch.object(main, "run_script") as run_script_mock,
        patch.object(main, "wait_for_data", return_value=None),
        patch.object(main, "append_unique_lines", return_value=0),
    ):
        driver.execute_script.side_effect = [[], [], {}, None]
        main.main()

    run_script_mock.assert_any_call(driver, main.NAVIGATION_SCRIPT)
    driver.get_log.assert_called_once_with("browser")


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

    out_file = tmp_path / "out.txt"

    with (
        patch.object(main, "SCRIPT_DIR", tmp_path),
        patch.object(main.time, "sleep"),
    ):
        main.run_script(driver, "collect.js")
        data = main.wait_for_data(driver, timeout=1)

    assert data == expected

    main.save_to_txt(data, out_file)

    contents = out_file.read_text(encoding="utf-8").strip()
    assert contents == "\t".join(str(expected[0].get(k, "")) for k in main.FIELD_ORDER)


def test_main_prints_mid_category_logs(capsys):
    driver = Mock()
    driver.get_log = Mock(return_value=[])

    def exec_script(arg):
        if arg == "return window.__midCategoryLogs__ || []":
            return ["log1", "log2"]

    driver.execute_script.side_effect = exec_script

    with (
        patch.object(main, "create_driver", return_value=driver),
        patch.object(main, "login_bgf", return_value=True),
        patch.object(main, "close_popups_after_delegate"),
        patch.object(main, "wait_for_mix_ratio_page", return_value=True),
        patch.object(main, "run_script") as run_script_mock,
        patch.object(main, "wait_for_data", return_value=None),
    ):
        main.main()

    run_script_mock.assert_any_call(driver, main.NAVIGATION_SCRIPT)
    driver.execute_script.assert_any_call("return window.__midCategoryLogs__ || []")
    driver.get_log.assert_called_once_with("browser")
    out = capsys.readouterr().out
    assert "중분류 클릭 로그" in out
    assert "['log1', 'log2']" in out


def test_main_converts_txt_to_excel(tmp_path):
    driver = Mock()
    driver.get_log = Mock(return_value=[])

    date_str = datetime.now().strftime("%y%m%d")
    out_dir = tmp_path / "code_outputs"

    with (
        patch.object(main, "CODE_OUTPUT_DIR", out_dir),
        patch.object(main, "create_driver", return_value=driver),
        patch.object(main, "login_bgf", return_value=True),
        patch.object(main, "close_popups_after_delegate"),
        patch.object(main, "wait_for_mix_ratio_page", return_value=True),
        patch.object(main, "run_script"),
        patch.object(main, "wait_for_data", return_value=None),
        patch.object(main, "append_unique_lines", return_value=0),
        patch.object(main, "is_7days_data_available", return_value=True),
        patch.object(main, "convert_txt_to_excel") as convert_mock,
        patch.object(main.time, "sleep"),
    ):
        driver.execute_script.side_effect = [[], [], {}, None]
        main.main()

    expected_txt = out_dir / f"{date_str}.txt"
    expected_excel = out_dir / "mid_excel" / f"{date_str}.xlsx"
    convert_mock.assert_called_once_with(str(expected_txt), str(expected_excel))


def test_main_writes_sales_data(tmp_path):
    driver = Mock()
    driver.get_log = Mock(return_value=[])

    out_dir = tmp_path / "code_outputs"
    parsed = [{"x": 1}]

    with (
        patch.object(main, "CODE_OUTPUT_DIR", out_dir),
        patch.object(main, "create_driver", return_value=driver),
        patch.object(main, "login_bgf", return_value=True),
        patch.object(main, "close_popups_after_delegate"),
        patch.object(main, "wait_for_mix_ratio_page", return_value=True),
        patch.object(main, "run_script"),
        patch.object(main, "wait_for_data", return_value=None),
        patch.object(main, "append_unique_lines", return_value=0),
        patch.object(main, "convert_txt_to_excel"),
        patch.object(main, "is_7days_data_available", return_value=True),
        patch.object(main.time, "sleep"),
        patch.object(main, "write_sales_data") as write_mock,
    ):
        driver.execute_script.side_effect = [[], [], parsed, None]
        main.main()

    db_path = out_dir / f"{datetime.now():%Y%m%d}.db"
    write_mock.assert_called_once_with(parsed, db_path)


def test_main_writes_past7_db_when_needed(tmp_path):
    driver = Mock()
    driver.get_log = Mock(return_value=[])

    out_dir = tmp_path / "code_outputs"
    parsed = [{"x": 1}]

    with (
        patch.object(main, "CODE_OUTPUT_DIR", out_dir),
        patch.object(main, "create_driver", return_value=driver),
        patch.object(main, "login_bgf", return_value=True),
        patch.object(main, "close_popups_after_delegate"),
        patch.object(main, "wait_for_mix_ratio_page", return_value=True),
        patch.object(main, "run_script"),
        patch.object(main, "execute_collect_single_day_data", return_value={"success": True, "data": []}),
        patch.object(main, "get_past_dates", return_value=["20240101"]),
        patch.object(main, "wait_for_data", return_value=None),
        patch.object(main, "append_unique_lines", return_value=0),
        patch.object(main, "convert_txt_to_excel"),
        patch.object(main, "is_7days_data_available", return_value=False),
        patch.object(main.time, "sleep"),
        patch.object(main, "write_sales_data") as write_mock,
    ):
        driver.execute_script.side_effect = [[], [], parsed, None]
        main.main()

    expected = out_dir / main.PAST7_DB_FILE
    write_mock.assert_called_once_with(parsed, expected)


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
    assert result.returncode == 0
    assert 'MAIN CALLED' in result.stdout
