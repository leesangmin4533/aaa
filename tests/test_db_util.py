import importlib.util
import pathlib
import sqlite3

_spec = importlib.util.spec_from_file_location(
    "db_util",
    pathlib.Path(__file__).resolve().parents[1] / "utils" / "db_util.py",
)
db_util = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(db_util)


def _read_rows(db_path: pathlib.Path) -> list[tuple[str, int]]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT product_code, sales FROM mid_sales ORDER BY id")
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
    assert _read_rows(db_path) == [("111", 5)]
    db_path.unlink()
    assert not db_path.exists()


def test_write_sales_data_inserts_only_when_sales_increase(tmp_path):
    db_path = tmp_path / "sales.db"
    record = {"productCode": "222", "sales": 3}
    assert db_util.write_sales_data([record], db_path) == 1
    assert _read_rows(db_path) == [("222", 3)]

    # same sales should not insert
    assert db_util.write_sales_data([record], db_path) == 0
    assert _read_rows(db_path) == [("222", 3)]

    # increased sales should insert
    higher = {"productCode": "222", "sales": 5}
    assert db_util.write_sales_data([higher], db_path) == 1
    assert _read_rows(db_path) == [("222", 3), ("222", 5)]
    db_path.unlink()
    assert not db_path.exists()
