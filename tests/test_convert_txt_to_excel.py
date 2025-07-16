import importlib.util
import pathlib
import pandas as pd

_spec = importlib.util.spec_from_file_location(
    "convert_txt_to_excel",
    pathlib.Path(__file__).resolve().parents[1] / "utils" / "convert_txt_to_excel.py",
)
convert_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(convert_module)


def test_convert_txt_to_excel(tmp_path):
    txt = tmp_path / "sample.txt"
    txt.write_text("001\tmid\t111\tprod\t1\t2\t3\t4\t5\n", encoding="utf-8")

    out_file = tmp_path / "out.xlsx"
    out_path = convert_module.convert_txt_to_excel(str(txt), str(out_file))
    assert out_path.exists()

    df = pd.read_excel(out_path, dtype=str)
    assert list(df.columns) == [
        "중분류코드",
        "중분류명",
        "상품코드",
        "상품명",
        "매출",
        "발주",
        "매입",
        "폐기",
        "현재고",
    ]
    assert df.iloc[0].tolist() == [
        "001",
        "mid",
        "111",
        "prod",
        "1",
        "2",
        "3",
        "4",
        "5",
    ]

