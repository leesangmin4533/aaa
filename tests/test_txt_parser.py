import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "txt_parser",
    pathlib.Path(__file__).resolve().parents[1] / "utils" / "txt_parser.py",
)
txt_parser = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(txt_parser)


def test_parse_txt_basic(tmp_path):
    txt = tmp_path / "sample.txt"
    txt.write_text("001\tmid\t111\tprod\t5\t1\t2\t3\t4\n", encoding="utf-8")
    records = txt_parser.parse_txt(txt)
    assert records == [
        {
            "midCode": "001",
            "midName": "mid",
            "productCode": "111",
            "productName": "prod",
            "sales": 5,
            "order": 1,
            "purchase": 2,
            "discard": 3,
            "stock": 4,
        }
    ]


def test_parse_txt_handles_missing_values(tmp_path):
    txt = tmp_path / "sample.txt"
    txt.write_text("001\tmid\t111\tprod\t5\t1\t2\t-\t\n", encoding="utf-8")
    records = txt_parser.parse_txt(txt)
    rec = records[0]
    assert rec["discard"] == 0
    assert rec["stock"] == 0
