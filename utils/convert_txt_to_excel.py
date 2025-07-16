from __future__ import annotations

from datetime import datetime
from pathlib import Path
import pandas as pd


def convert_txt_to_excel(
    txt_path: str, output_path: str | Path | None = None, encoding: str = "utf-8"
) -> Path:
    """Convert a pipe-delimited text file to an Excel file with one sheet.

    Parameters
    ----------
    txt_path: str
        Path to the input text file.
    output_path: str | Path | None, optional
        Destination Excel file path. If omitted, a file named
        ``매출분석_YYYYMMDD.xlsx`` is created next to ``txt_path``.
    encoding: str, default "utf-8"
        Encoding of the text file.

    Returns
    -------
    Path
        Path to the generated Excel file.
    """
    txt_path = Path(txt_path)
    df = pd.read_csv(txt_path, sep="\t", header=None, encoding=encoding)
    df.columns = [
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
    if output_path is None:
        out_name = datetime.now().strftime("매출분석_%Y%m%d.xlsx")
        output_path = txt_path.with_name(out_name)
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_excel(output_path, index=False)
    return Path(output_path)
