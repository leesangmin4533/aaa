import importlib.util
import pathlib
import sys
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

spec = importlib.util.spec_from_file_location(
    "analysis.product_exporter",
    pathlib.Path(__file__).resolve().parents[1] / "analysis" / "product_exporter.py",
)
product_exporter = importlib.util.module_from_spec(spec)
sys.modules["analysis.product_exporter"] = product_exporter
spec.loader.exec_module(product_exporter)


def test_export_product_data_writes_file(tmp_path):
    rows = [
        {
            "중분류코드": "201",
            "중분류텍스트": "음료",
            "상품코드": "8801234567890",
            "상품명": "주)압도적리치참치마요2",
            "매출": "1",
            "발주": "1",
            "매입": "",
            "폐기": "0",
            "현재고": "",
        }
    ]

    class D(product_exporter.datetime.date):
        @classmethod
        def today(cls):
            return cls(2025, 7, 8)

    with patch.object(product_exporter.datetime, "date", D):
        path = product_exporter.export_product_data(rows, tmp_path)

    assert path.name == "20250708.txt"
    assert path.exists()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "\t".join(product_exporter.HEADER)
    assert lines[1].split("\t")[2] == "8801234567890"
