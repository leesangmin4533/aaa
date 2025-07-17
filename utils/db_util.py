from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import sys

if __package__:
    from .log_util import create_logger
else:  # pragma: no cover - fallback when executed directly
    sys.path.append(str(Path(__file__).resolve().parent))
    from log_util import create_logger

log = create_logger("db_util")


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS mid_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collected_at TEXT,
    mid_code TEXT,
    mid_name TEXT,
    product_code TEXT,
    product_name TEXT,
    sales INTEGER,
    order_cnt INTEGER,
    purchase INTEGER,
    disposal INTEGER,
    stock INTEGER
);
"""


def init_db(path: Path) -> sqlite3.Connection:
    """Open ``path`` and ensure the ``mid_sales`` table exists."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    return conn


def _get_value(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record:
            return record[key]
    return None


def write_sales_data(records: list[dict[str, Any]], db_path: Path) -> int:
    """Insert sales records only when ``sales`` increased.

    Parameters
    ----------
    records : list[dict[str, Any]]
        Parsed sales data records.
    db_path : Path
        SQLite database file path.

    Returns
    -------
    int
        Number of rows inserted.
    """
    conn = init_db(db_path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    cur = conn.cursor()
    inserted = 0
    for rec in records:
        product_code = _get_value(rec, "productCode", "product_code")
        sales = _get_value(rec, "sales")
        if product_code is None or sales is None:
            continue
        cur.execute(
            "SELECT sales FROM mid_sales WHERE product_code=? ORDER BY id DESC LIMIT 1",
            (product_code,),
        )
        row = cur.fetchone()
        last_sales = row[0] if row else None
        if last_sales is not None and isinstance(sales, (int, float)) and sales <= last_sales:
            log("write", "DEBUG", f"{product_code}: prev={last_sales}, new={sales} -> skipped")
            continue
        if last_sales is not None:
            log("write", "INFO", f"{product_code}: prev={last_sales}, new={sales}")
        cur.execute(
            """
            INSERT INTO mid_sales (
                collected_at, mid_code, mid_name, product_code, product_name,
                sales, order_cnt, purchase, disposal, stock
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
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
        inserted += 1
    conn.commit()
    conn.close()
    log("write", "INFO", f"inserted {inserted} rows")
    return inserted
