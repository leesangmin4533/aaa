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
analysis_spec = importlib.util.spec_from_file_location(
    "analysis", pathlib.Path(__file__).resolve().parents[1] / "analysis" / "__init__.py"
)
analysis = importlib.util.module_from_spec(analysis_spec)
sys.modules["analysis"] = analysis
analysis_spec.loader.exec_module(analysis)

spec = importlib.util.spec_from_file_location(
    "analysis.product_exporter",
    pathlib.Path(__file__).resolve().parents[1] / "analysis" / "product_exporter.py",
)
product_exporter = importlib.util.module_from_spec(spec)
sys.modules["analysis.product_exporter"] = product_exporter
spec.loader.exec_module(product_exporter)


class DummyDF:
    def __init__(self):
        self._rows = [
            {"code": "201", "name": "음료"},
        ]

    def iterrows(self):
        for idx, row in enumerate(self._rows):
            yield idx, row


def test_export_product_data_writes_file(tmp_path):
    driver = Mock()
    driver.execute_script.side_effect = [
        None,
        ["8801234567890"],
        None,
        {
            "상품코드": "8801234567890",
            "상품명": "주)압도적리치참치마요2",
            "매출": "1",
            "발주": "1",
            "매입": "0",
            "폐기": "0",
            "현재고": "3",
        },
    ]

    df = DummyDF()
    class D(product_exporter.datetime.date):
        @classmethod
        def today(cls):
            return cls(2025, 7, 8)

    with patch.object(analysis, "parse_mix_ratio_data", return_value=df), \
         patch.object(product_exporter.time, "sleep"), \
         patch.object(product_exporter.datetime, "date", D):
        path = product_exporter.export_product_data(driver, tmp_path)

    assert path.name == "20250708.txt"
    assert path.exists()
    driver.execute_script.assert_called()
