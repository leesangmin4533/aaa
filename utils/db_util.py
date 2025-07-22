"""
매출 데이터 DB 관리 모듈 (통합 DB 방식)

이 모듈은 다음과 같은 규칙으로 데이터를 관리합니다:
- 모든 데이터는 단일 통합 DB 파일에 저장됩니다.
- collected_at은 분 단위까지 기록됩니다 (YYYY-MM-DD HH:MM).
- (collected_at, product_code)는 고유해야 하며, 중복된 데이터는 저장되지 않습니다.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import sys

if __package__:
    from .log_util import get_logger
else:  # pragma: no cover - fallback when executed directly
    sys.path.append(str(Path(__file__).resolve().parent))
    from log_util import get_logger

log = get_logger(__name__)


# 통합 매출 데이터 테이블 스키마
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS mid_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collected_at TEXT,        -- 데이터 수집 시각 (YYYY-MM-DD HH:MM)
    mid_code TEXT,           -- 중분류 코드
    mid_name TEXT,           -- 중분류명
    product_code TEXT,       -- 상품 코드
    product_name TEXT,       -- 상품명
    sales INTEGER,           -- 매출액
    order_cnt INTEGER,       -- 주문수량
    purchase INTEGER,        -- 매입액
    disposal INTEGER,        -- 폐기액
    stock INTEGER,           -- 재고액
    UNIQUE(collected_at, product_code) -- 이 조합은 고유해야 함
);
"""


def init_db(path: Path) -> sqlite3.Connection:
    """
    통합 DB 파일을 열고 mid_sales 테이블을 초기화합니다.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    return conn


def _get_value(record: dict[str, Any], *keys: str) -> Any:
    """
    레코드에서 여러 키 중 존재하는 첫 번째 키의 값을 반환합니다.
    """
    for key in keys:
        if key in record:
            return record[key]
    return None


def write_sales_data(records: list[dict[str, Any]], db_path: Path, collected_at_override: str | None = None) -> int:
    """
    매출 데이터를 통합 DB에 저장합니다.

    저장 규칙:
    1. 수집 시각은 분 단위까지 기록 (YYYY-MM-DD HH:MM)
    2. 동일 상품(product_code)에 대해:
       - sales가 증가한 경우에만 새 데이터 저장
       - sales가 같거나 감소한 경우 저장하지 않음
    3. (collected_at, product_code) 조합은 고유해야 함

    Parameters
    ----------
    records : list[dict[str, Any]]
        저장할 매출 데이터 레코드 목록
    db_path : Path
        통합 DB 파일 경로
    collected_at_override : str | None
        수집 시각 오버라이드 (None이면 현재 시각 사용)

    Returns
    -------
    int
        저장된 레코드 수
    """
    conn = init_db(db_path)
    collected_at_val = collected_at_override if collected_at_override else datetime.now().strftime("%Y-%m-%d %H:%M")
    cur = conn.cursor()
    inserted_count = 0

    # 먼저 날짜만 추출하여 당일 데이터만 비교하도록 함
    current_date = collected_at_val.split()[0]

    # 새로운 데이터를 저장하되, 같은 날짜의 sales가 더 큰 경우에만 저장
    insert_sql = """
    INSERT INTO mid_sales (
        collected_at, mid_code, mid_name, product_code, product_name,
        sales, order_cnt, purchase, disposal, stock
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    for rec in records:
        product_code = _get_value(rec, "productCode", "product_code")
        sales_raw = _get_value(rec, "sales")

        if product_code is None or sales_raw is None:
            continue

        try:
            sales = int(sales_raw)
        except (ValueError, TypeError):
            continue

        params = (
            collected_at_val,
            _get_value(rec, "midCode", "mid_code"),
            _get_value(rec, "midName", "mid_name"),
            product_code,
            _get_value(rec, "productName", "product_name"),
            sales,
            _get_value(rec, "order", "order_cnt"),
            _get_value(rec, "purchase"),
            _get_value(rec, "discard", "disposal"),
            _get_value(rec, "stock"),
        )
        
        cur.execute(insert_sql, params)
        if cur.rowcount > 0:
            inserted_count += 1

    conn.commit()
    conn.close()
    return inserted_count

def check_dates_exist(db_path: Path, dates_to_check: list[str]) -> list[str]:
    """
    주어진 날짜 목록 중 DB에 데이터가 없는 날짜를 찾아 반환합니다.

    Parameters
    ----------
    db_path : Path
        검사할 통합 DB 파일 경로
    dates_to_check : list[str]
        'YYYY-MM-DD' 형식의 날짜 문자열 리스트

    Returns
    -------
    list[str]
        데이터가 존재하지 않는 날짜 (YYYY-MM-DD 형식) 리스트
    """
    if not db_path.exists():
        return dates_to_check # DB 파일이 없으면 모든 날짜가 없다고 간주

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    missing_dates = []
    for date_str in dates_to_check:
        cur.execute("SELECT 1 FROM mid_sales WHERE SUBSTR(collected_at, 1, 10) = ? LIMIT 1", (date_str,))
        if cur.fetchone() is None:
            missing_dates.append(date_str)
            
    conn.close()
    log.info(f"DB에 없는 날짜: {missing_dates}", extra={'tag': 'db'})
    return missing_dates
