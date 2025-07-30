# utils/hourly_sales_util.py
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any, List, Dict
from datetime import datetime

def init_hourly_db(db_path: Path) -> sqlite3.Connection:
    """증분 저장을 위한 테이블과 스냅샷 테이블 초기화."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS hourly_sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        hour TEXT,
        product_code TEXT,
        mid_code TEXT,
        sales_inc INTEGER,
        order_cnt_inc INTEGER,
        purchase_inc INTEGER,
        disposal_inc INTEGER,
        stock_inc INTEGER, -- 재고 증감분
        stock INTEGER, -- 현재 재고 상태
        UNIQUE(date, hour, product_code, mid_code)
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS daily_snapshot (
        date TEXT,
        product_code TEXT,
        mid_code TEXT,
        sales INTEGER,
        order_cnt INTEGER,
        purchase INTEGER,
        disposal INTEGER,
        stock INTEGER,
        PRIMARY KEY (date, product_code, mid_code)
    )
    """)
    conn.commit()
    return conn

def write_hourly_data(records: List[Dict[str, Any]], collected_at: str, db_path: Path) -> int:
    """
    기존 누적값과 비교해 증가분만 hourly_sales 테이블에 저장하고,
    daily_snapshot 테이블을 업데이트한다.

    Parameters
    ----------
    records : list of dict
        현재 수집된 전체 데이터 (누적값).
    collected_at : str
        수집 시각 문자열 ('YYYY-MM-DD HH:MM' 포맷).
    db_path : Path
        DB 파일 경로.

    Returns
    -------
    int : 저장된 행 수
    """
    conn = init_hourly_db(db_path)
    cur = conn.cursor()
    date_part = collected_at.split()[0]
    hour_part = collected_at.split()[1][:2]  # 'HH'

    inserted = 0
    for rec in records:
        product_code = rec.get("productCode") or rec.get("product_code")
        mid_code = rec.get("midCode") or rec.get("mid_code")
        # 현재 누적값
        sales = int(rec.get("sales") or rec.get("SALE_QTY") or 0)
        order_cnt = int(rec.get("order_cnt") or rec.get("ORD_QTY") or 0)
        purchase = int(rec.get("purchase") or rec.get("BUY_QTY") or 0)
        disposal = int(rec.get("disposal") or rec.get("DISUSE_QTY") or 0)
        stock = int(rec.get("stock") or rec.get("STOCK_QTY") or 0)

        # 스냅샷에서 직전 누적값 조회
        cur.execute("""
        SELECT sales, order_cnt, purchase, disposal, stock
          FROM daily_snapshot
         WHERE date = ? AND product_code = ? AND mid_code = ?
        """, (date_part, product_code, mid_code))
        row = cur.fetchone()
        prev_sales, prev_order, prev_purchase, prev_disposal, prev_stock = row if row else (0, 0, 0, 0, 0)

        # 증감분 계산 (음수 포함)
        sales_inc = sales - prev_sales
        order_inc = order_cnt - prev_order
        purchase_inc = purchase - prev_purchase
        disposal_inc = disposal - prev_disposal
        stock_inc = stock - prev_stock

        # 변경분이 있는 경우에만 hourly_sales 저장
        if any([sales_inc, order_inc, purchase_inc, disposal_inc, stock_inc]):
            cur.execute("""
            INSERT OR REPLACE INTO hourly_sales
            (date, hour, product_code, mid_code, sales_inc, order_cnt_inc, purchase_inc, disposal_inc, stock_inc, stock)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (date_part, hour_part, product_code, mid_code,
                  sales_inc, order_inc, purchase_inc, disposal_inc, stock_inc, stock))
            inserted += 1

        # 스냅샷 업데이트
        cur.execute("""
        INSERT OR REPLACE INTO daily_snapshot
        (date, product_code, mid_code, sales, order_cnt, purchase, disposal, stock)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (date_part, product_code, mid_code, sales, order_cnt, purchase, disposal, stock))

    conn.commit()
    conn.close()
    return inserted
