from __future__ import annotations

from pathlib import Path
import pandas as pd

COLUMNS = [
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


def convert_txt_to_excel(txt_path: str | Path, out_path: str | Path) -> Path:
    """Convert a tab-separated text file to an Excel file.

    Parameters
    ----------
    txt_path : str | Path
        Input text file containing tab separated values.
    out_path : str | Path
        Output Excel file path.
    Returns
    -------
    Path
        Path to the created Excel file.
    """
    txt_path = Path(txt_path)
    out_path = Path(out_path)

    df = pd.read_csv(txt_path, sep="\t", header=None, names=COLUMNS, dtype=str)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out_path, index=False, engine="openpyxl")
    return out_path
