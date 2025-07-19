from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys
import pandas as pd

if __package__:
    from .log_util import get_logger
else:  # pragma: no cover - fallback when executed directly
    sys.path.append(str(Path(__file__).resolve().parent))
    from log_util import create_logger

log = get_logger(__name__)


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
    log("convert", "INFO", f"텍스트 파일 읽기 시도: {txt_path}")
    try:
        df = pd.read_csv(
            txt_path,
            sep="\t",
            header=None,
            dtype=str,
            encoding=encoding,
        )
    except Exception as e:
        log("convert", "ERROR", f"텍스트 파일 읽기 실패: {e}")
        raise

    log("convert", "INFO", f"{len(df)}개 행 로드 완료")
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

    for col in ["매출", "발주", "매입", "폐기", "현재고"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if output_path is None:
        out_name = datetime.now().strftime("매출분석_%Y%m%d.xlsx")
        output_path = txt_path.with_name(out_name)
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    log("convert", "INFO", f"엑셀 파일 저장 위치: {output_path}")
    try:
        with pd.ExcelWriter(
            output_path,
            engine="xlsxwriter",
            engine_kwargs={"options": {"strings_to_numbers": False}},
        ) as writer:
            df.to_excel(writer, index=False)
    except Exception as e:
        log("convert", "ERROR", f"엑셀 저장 실패: {e}")
        raise
    log("convert", "INFO", "엑셀 파일 저장 완료")
    return Path(output_path)
