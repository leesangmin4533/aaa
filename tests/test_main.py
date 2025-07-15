import importlib.util
import pathlib
import sys
import types
from datetime import datetime
from unittest.mock import Mock, patch
import pytest

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

class DesiredCapabilities:
    CHROME = {}
dcaps_pkg.DesiredCapabilities = DesiredCapabilities

selenium_pkg.webdriver = webdriver_pkg
sys.modules.setdefault("selenium", selenium_pkg)
sys.modules.setdefault("selenium.webdriver", webdriver_pkg)
sys.modules.setdefault("selenium.webdriver.remote", remote_pkg)
sys.modules.setdefault("selenium.webdriver.remote.webdriver", webdriver_module)
sys.modules.setdefault("selenium.webdriver.chrome", chrome_pkg)
sys.modules.setdefault("selenium.webdriver.chrome.service", service_pkg)
sys.modules.setdefault("selenium.webdriver.chrome.options", options_pkg)
sys.modules.setdefault("selenium.webdriver.common", common_pkg)
sys.modules.setdefault("selenium.webdriver.common.desired_capabilities", dcaps_pkg)
sys.modules.setdefault("selenium.webdriver.common", common_pkg)
sys.modules.setdefault("selenium.webdriver.common.desired_capabilities", dcaps_pkg)

# dummy login module
login_pkg = types.ModuleType("login")
login_bgf_pkg = types.ModuleType("login.login_bgf")
def dummy_login_bgf(*a, **k):
    return True
login_bgf_pkg.login_bgf = dummy_login_bgf
login_pkg.login_bgf = login_bgf_pkg
sys.modules.setdefault("login", login_pkg)
sys.modules.setdefault("login.login_bgf", login_bgf_pkg)

popup_pkg = types.ModuleType("utils.popup_util")
def dummy_close_popups_after_delegate(*a, **k):
    pass
popup_pkg.close_popups_after_delegate = dummy_close_popups_after_delegate
sys.modules.setdefault("utils.popup_util", popup_pkg)

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

    with (
        patch.object(main, "create_driver", return_value=driver),
        patch.object(main, "login_bgf", return_value=True),
        patch.object(main, "close_popups_after_delegate"),
        patch.object(main, "navigate_to_category_mix_ratio", return_value=True) as nav,
        patch.object(main, "wait_for_mix_ratio_page", return_value=True),
        patch.object(main, "run_script"),
        patch.object(main, "wait_for_data", return_value=None),
    ):
        main.main()

    nav.assert_called_once_with(driver)
