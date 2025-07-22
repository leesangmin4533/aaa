"""
매출 데이터 DB 관리 모듈

이 모듈은 다음과 같은 규칙으로 데이터를 관리합니다:
- DB가 기준이며, 텍스트는 보조 용도입니다.
- 텍스트의 모든 항목을 DB에 저장합니다.
- collected_at은 분 단위까지 기록됩니다 (YYYY-MM-DD HH:MM).
- 실행 시각 기준으로 기록이 남습니다.
- 같은 날 DB 내에서 product_code가 동일하고 sales가 증가하지 않으면 저장하지 않습니다.
- 하루에 하나의 DB 파일이 생성됩니다 (예: 20250718.db).
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


# 매출 데이터 테이블 스키마
# - collected_at: 데이터 수집 시각 (YYYY-MM-DD HH:MM)
# - mid_code/name: 중분류 코드와 이름
# - product_code/name: 상품 코드와 이름
# - sales: 매출액
# - order_cnt: 주문수량
# - purchase: 매입액
# - disposal: 폐기액
# - stock: 재고액
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
    stock INTEGER           -- 재고액
);
"""


def init_db(path: Path) -> sqlite3.Connection:
    """
    DB 파일을 열고 mid_sales 테이블이 존재하는지 확인합니다.
    
    Parameters
    ----------
    path : Path
        DB 파일 경로 (예: code_outputs/20250718.db)
        
    Returns
    -------
    sqlite3.Connection
        초기화된 DB 연결 객체
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
    
    Parameters
    ----------
    record : dict[str, Any]
        검색할 레코드
    *keys : str
        검색할 키 목록 (순서대로 검색)
        
    Returns
    -------
    Any
        찾은 값 또는 None
    """
    for key in keys:
        if key in record:
            return record[key]
    return None


def write_sales_data(records: list[dict[str, Any]], db_path: Path, collected_at_override: str | None = None, skip_sales_check: bool = False) -> int:
    """
    """
    매출 데이터를 DB에 저장합니다.

    동작 규칙:
    1. 모든 수집 결과는 이 함수로 전달됩니다.
    2. collected_at은 현재 시각(분 단위)으로 기록됩니다.
    3. 같은 날짜의 DB 내에서 product_code가 동일한 경우:
       - 이미 존재하면 기존 레코드를 업데이트합니다.
       - 존재하지 않으면 새로운 레코드를 삽입합니다.
    4. DB 파일은 날짜별로 새로 생성됩니다 (예: 20250718.db)

    Parameters
    ----------
    records : list[dict[str, Any]]
        텍스트 파일에서 파싱된 매출 데이터 레코드 목록
    db_path : Path
        SQLite DB 파일 경로 (예: code_outputs/20250718.db)
    collected_at_override : str | None, optional
        수집 시각을 강제로 지정할 때 사용 (YYYY-MM-DD HH:MM). 기본값은 현재 시각.
    skip_sales_check : bool, optional
        이 파라미터는 현재 Upsert 로직에 직접적인 영향을 주지 않습니다.
        과거 데이터 수집 시 `main.py`에서 `True`로 전달되지만,
        `write_sales_data` 함수는 항상 `product_code`와 날짜를 기준으로
        중복을 확인하고 업데이트/삽입을 수행합니다.

    Returns
    -------
    int
        실제로 처리(삽입 또는 업데이트)된 레코드 수
    """
    """
    conn = init_db(db_path)
    collected_at_val = collected_at_override if collected_at_override else datetime.now().strftime("%Y-%m-%d %H:%M")
    cur = conn.cursor()
    processed_count = 0

    for rec in records:
        product_code = _get_value(rec, "productCode", "product_code")
        sales_raw = _get_value(rec, "sales")

        if product_code is None or sales_raw is None:
            log.warning(f"Skipping record due to missing product_code or sales: {rec}", extra={'tag': 'db'})
            continue

        try:
            sales = int(sales_raw)
        except (ValueError, TypeError):
            log.warning(f"Skipping record due to invalid sales value: {sales_raw} in {rec}", extra={'tag': 'db'})
            continue

        date_part = collected_at_val.split(' ')[0]  # YYYY-MM-DD 부분 추출

        # 해당 날짜와 product_code로 기존 레코드가 있는지 확인
        cur.execute(
            "SELECT id FROM mid_sales WHERE product_code=? AND SUBSTR(collected_at, 1, 10) = ?",
            (product_code, date_part),
        )
        existing_id_row = cur.fetchone()

        if existing_id_row:
            # 레코드가 존재하면 업데이트
            existing_id = existing_id_row[0]
            log.debug(f"Updating existing record for product_code={product_code} on {date_part} (ID: {existing_id}).", extra={'tag': 'db'})
            cur.execute(
                """
                UPDATE mid_sales SET
                    collected_at = ?, mid_code = ?, mid_name = ?, product_name = ?,
                    sales = ?, order_cnt = ?, purchase = ?, disposal = ?, stock = ?
                WHERE id = ?
                """,
                (
                    collected_at_val,
                    _get_value(rec, "midCode", "mid_code"),
                    _get_value(rec, "midName", "mid_name"),
                    _get_value(rec, "productName", "product_name"),
                    sales,
                    _get_value(rec, "order", "order_cnt"),
                    _get_value(rec, "purchase"),
                    _get_value(rec, "discard", "disposal"),
                    _get_value(rec, "stock"),
                    existing_id
                ),
            )
        else:
            # 레코드가 존재하지 않으면 삽입
            log.debug(f"Inserting new record for product_code={product_code} on {date_part}.", extra={'tag': 'db'})
            cur.execute(
                """
                INSERT INTO mid_sales (
                    collected_at, mid_code, mid_name, product_code, product_name,
                    sales, order_cnt, purchase, disposal, stock
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
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
                ),
            )
        processed_count += 1

    conn.commit()
    conn.close()
    return processed_count

def is_7days_data_available(db_path: Path) -> bool:
    """
    Checks if there are at least 7 consecutive days of data in the mid_sales table,
    starting from the most recent date.
    """
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        # Get all distinct dates, ordered descending
        cur.execute("SELECT DISTINCT SUBSTR(collected_at, 1, 10) FROM mid_sales ORDER BY SUBSTR(collected_at, 1, 10) DESC")
        distinct_dates_str = [row[0] for row in cur.fetchall()]

        if len(distinct_dates_str) < 7:
            log.info(f"Less than 7 distinct dates ({len(distinct_dates_str)}) found in DB.", extra={'tag': 'db'})
            return False

        # Convert date strings to datetime objects
        distinct_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in distinct_dates_str]

        # Check for 7 consecutive days
        for i in range(6): # Check 6 gaps for 7 consecutive days
            if i + 1 < len(distinct_dates):
                diff = (distinct_dates[i] - distinct_dates[i+1]).days
                if diff != 1:
                    log.info(f"Gap found between {distinct_dates[i]} and {distinct_dates[i+1]}. Not 7 consecutive days.", extra={'tag': 'db'})
                    return False
            else: # Not enough dates to check 6 gaps
                log.info(f"Not enough dates ({len(distinct_dates)}) to check for 7 consecutive days.", extra={'tag': 'db'})
                return False

        log.info(f"Found 7 consecutive days of data in DB, ending with {distinct_dates[0]}.", extra={'tag': 'db'})
        return True

    except sqlite3.Error as e:
        log.error(f"Database error while checking 7-day data: {e}", extra={'tag': 'db'}, exc_info=True)
        return False
    except Exception as e:
        log.error(f"An unexpected error occurred while checking 7-day data: {e}", extra={'tag': 'db'}, exc_info=True)
        return False
    finally:
        if conn:
            conn.close()
