import importlib.util
import pathlib
import sqlite3
from datetime import datetime

import pandas as pd

_spec = importlib.util.spec_from_file_location(
    "db_util",
    pathlib.Path(__file__).resolve().parents[1] / "utils" / "db_util.py",
)
db_util = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(db_util)


def _read_rows(db_path: pathlib.Path) -> list[tuple[str, str, int, float, float]]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT collected_at, product_code, sales, temperature, rainfall FROM mid_sales ORDER BY id"
    )
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
    ts, code, sales, _, _ = rows[0]
    assert code == "111" and sales == 5
    # verify collected_at uses YYYY-MM-DD HH:MM format
    parsed = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
    assert parsed.strftime("%Y-%m-%d %H:%M:%S") == ts
    db_path.unlink()
    assert not db_path.exists()


def test_write_sales_data_updates_existing_record(tmp_path, monkeypatch):
    db_path = tmp_path / "sales.db"
    weather_iter = iter(
        [
            pd.DataFrame([{"temperature": 10.0, "rainfall": 1.0}]),
            pd.DataFrame([{"temperature": 5.0, "rainfall": 2.0}]),
        ]
    )
    monkeypatch.setattr(db_util, "get_weather_data", lambda dates: next(weather_iter))

    record = {"productCode": "222", "sales": 3}

    # 첫 저장
    assert db_util.write_sales_data([record], db_path) == 1
    rows = _read_rows(db_path)
    assert len(rows) == 1
    ts, code, sales, temp, rain = rows[0]
    assert (code, sales, temp, rain) == ("222", 3, 10.0, 1.0)

    # sales가 증가하면 기존 레코드가 업데이트되지만 날씨는 그대로 유지됨
    higher = {"productCode": "222", "sales": 5}
    assert db_util.write_sales_data([higher], db_path) == 1
    rows = _read_rows(db_path)
    assert len(rows) == 1
    ts, code, sales, temp, rain = rows[0]
    assert (code, sales, temp, rain) == ("222", 5, 10.0, 1.0)
    db_path.unlink()
    assert not db_path.exists()


def test_write_sales_data_recall_keeps_weather(tmp_path, monkeypatch):
    db_path = tmp_path / "sales.db"
    weather_iter = iter(
        [
            pd.DataFrame([{"temperature": 12.0, "rainfall": 0.5}]),
            pd.DataFrame([{"temperature": 7.0, "rainfall": 3.0}]),
        ]
    )
    monkeypatch.setattr(db_util, "get_weather_data", lambda dates: next(weather_iter))

    record = {"productCode": "333", "sales": 2}

    assert db_util.write_sales_data([record], db_path) == 1
    assert db_util.write_sales_data([record], db_path) == 1
    rows = _read_rows(db_path)
    assert len(rows) == 1
    ts, code, sales, temp, rain = rows[0]
    assert (code, sales, temp, rain) == ("333", 2, 12.0, 0.5)
    db_path.unlink()
    assert not db_path.exists()


def test_write_sales_data_records_weather_for_new_product(tmp_path, monkeypatch):
    db_path = tmp_path / "sales.db"
    weather_iter = iter(
        [
            pd.DataFrame([{"temperature": 15.0, "rainfall": 0.0}]),
            pd.DataFrame([{"temperature": 8.0, "rainfall": 4.0}]),
        ]
    )
    monkeypatch.setattr(db_util, "get_weather_data", lambda dates: next(weather_iter))

    first = {"productCode": "444", "sales": 1}
    second = {"productCode": "555", "sales": 3}

    assert db_util.write_sales_data([first], db_path) == 1
    assert db_util.write_sales_data([second], db_path) == 2
    rows = sorted(_read_rows(db_path), key=lambda r: r[1])
    assert len(rows) == 2
    assert rows == [
        (rows[0][0], "444", 1, 15.0, 0.0),
        (rows[1][0], "555", 3, 8.0, 4.0),
    ]
    db_path.unlink()
    assert not db_path.exists()


def test_write_sales_data_creates_directory(tmp_path):
    nested = tmp_path / "nested" / "dir"
    db_path = nested / "sales.db"
    records = [{"productCode": "333", "sales": 1}]
    assert not nested.exists()
    db_util.write_sales_data(records, db_path)
    assert nested.exists()
