from __future__ import annotations

import datetime
from pathlib import Path
from typing import Iterable, Mapping

from utils.log_util import create_logger


HEADER = [
    "중분류코드",
    "중분류텍스트",
    "상품코드",
    "상품명",
    "매출",
    "발주",
    "매입",
    "폐기",
    "현재고",
]


def export_product_data(
    rows: Iterable[Mapping[str, str]],
    output_dir: str | Path = ".",
    delimiter: str = "\t",
) -> Path:
    """Save product data rows to a text file.

    Parameters
    ----------
    rows:
        상품 정보를 담은 ``dict`` 목록.
    output_dir:
        결과 파일을 저장할 디렉터리. 기본값은 현재 작업 디렉터리다.
    delimiter:
        열 구분자로 사용할 문자열. 기본값은 탭 문자("\t").
    """

    log = create_logger("export")

    data = list(rows)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = datetime.date.today().strftime("%Y%m%d.txt")
    path = output_dir / filename

    with open(path, "w", encoding="utf-8") as f:
        f.write(delimiter.join(HEADER) + "\n")
        for row in data:
            values = [str(row.get(col, "")) for col in HEADER]
            f.write(delimiter.join(values) + "\n")

    log("export", "INFO", f"총 {len(data)}행 저장: {path}")
    return path
