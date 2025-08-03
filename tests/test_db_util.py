import importlib.util
import pathlib
import sqlite3
from datetime import datetime

_spec = importlib.util.spec_from_file_location(
    "db_util",
    pathlib.Path(__file__).resolve().parents[1] / "utils" / "db_util.py",
)
db_util = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(db_util)


def _read_rows(db_path: pathlib.Path) -> list[tuple[str, str, int]]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT collected_at, product_code, sales FROM mid_sales ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return rows


def test_write_sales_data_inserts_records(tmp_path):
    db_path = tmp_path / "sales.db"
    records = [
        {
            "midCode": "001",
            "midName": "mid",
            "productCode": "111",
            "productName": "prod",
            "sales": 5,
            "order": 1,
            "purchase": 2,
            "discard": 0,
            "stock": 10,
        }
    ]
    inserted = db_util.write_sales_data(records, db_path)
    assert inserted == 1
    rows = _read_rows(db_path)
    assert len(rows) == 1
    ts, code, sales = rows[0]
    assert code == "111" and sales == 5
    # verify collected_at uses YYYY-MM-DD HH:MM format
    parsed = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == ts
    db_path.unlink()
    assert not db_path.exists()


def test_write_sales_data_updates_existing_record(tmp_path):
    db_path = tmp_path / "sales.db"
    record = {"productCode": "222", "sales": 3}

    # 첫 저장
    assert db_util.write_sales_data([record], db_path) == 1
    rows = _read_rows(db_path)
    assert len(rows) == 1
    assert [r[1:] for r in rows] == [("222", 3)]

    # 동일 sales로 호출 시 레코드가 중복 생성되지 않고 그대로 유지됨
    assert db_util.write_sales_data([record], db_path) == 1
    rows = _read_rows(db_path)
    assert len(rows) == 1
    assert [r[1:] for r in rows] == [("222", 3)]

    # sales가 증가하면 기존 레코드가 업데이트됨
    higher = {"productCode": "222", "sales": 5}
    assert db_util.write_sales_data([higher], db_path) == 1
    rows = _read_rows(db_path)
    assert len(rows) == 1
    assert [r[1:] for r in rows] == [("222", 5)]
    db_path.unlink()
    assert not db_path.exists()


def test_write_sales_data_creates_directory(tmp_path):
    nested = tmp_path / "nested" / "dir"
    db_path = nested / "sales.db"
    records = [{"productCode": "333", "sales": 1}]
    assert not nested.exists()
    db_util.write_sales_data(records, db_path)
    assert nested.exists()
