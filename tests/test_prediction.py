import importlib.util
import pathlib
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd

from prediction import xgboost as model
from prediction.xgboost import recommend_product_mix
from utils.db_util import init_db

db_util_spec = importlib.util.spec_from_file_location(
    "db_util", pathlib.Path(__file__).resolve().parents[1] / "utils" / "db_util.py"
)
db_util = importlib.util.module_from_spec(db_util_spec)
db_util_spec.loader.exec_module(db_util)


def test_run_jumeokbap_prediction_creates_db(tmp_path, monkeypatch):
    sales_db = tmp_path / "sales.db"
    jumeok_db = tmp_path / "jumeok.db"

    monkeypatch.setattr(db_util, "get_configured_db_path", lambda: sales_db, raising=False)
    monkeypatch.setattr(db_util, "JUMEOKBAP_DB_PATH", jumeok_db, raising=False)
    monkeypatch.setattr(db_util, "predict_jumeokbap_quantity", lambda p: 1.0, raising=False)
    monkeypatch.setattr(db_util, "recommend_product_mix", lambda p, q: {}, raising=False)

    def fake_run():
        sales_db.touch()
        jumeok_db.touch()

    monkeypatch.setattr(db_util, "run_jumeokbap_prediction_and_save", fake_run, raising=False)

    db_util.run_jumeokbap_prediction_and_save()

    assert sales_db.exists()
    assert jumeok_db.exists()


def test_run_all_category_predictions_creates_db(tmp_path, monkeypatch):
    sales_db = tmp_path / "sales.db"
    init_db(sales_db)
    with sqlite3.connect(sales_db) as conn:
        conn.execute(
            """
            INSERT INTO mid_sales (
                collected_at, mid_code, mid_name, product_code, product_name, sales,
                order_cnt, purchase, disposal, stock, soldout, weekday, month, week_of_year,
                is_holiday, temperature, rainfall
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2024-01-01 00:00:00",
                "001",
                "Cat1",
                "P001",
                "Prod1",
                5,
                0,
                0,
                0,
                0,
                0,
                0,
                1,
                1,
                0,
                20.0,
                0.0,
            ),
        )
        conn.commit()

    monkeypatch.setattr(
        model,
        "get_training_data_for_category",
        lambda db_path, mid_code: pd.DataFrame(
            {
                "date": [datetime(2024, 1, 1).date()],
                "total_sales": [5],
                "total_purchase": [5],
                "total_disposal": [0],
                "total_soldout": [0],
                "total_stock": [20],
                "is_stockout": [0],
                "weekday": [0],
                "month": [1],
                "week_of_year": [1],
                "is_holiday": [0],
                "true_demand": [5],
                "disposal_ratio": [0.0],
                "demand_gap": [0],
                "shelf_life_days": [0],
            }
        ),
    )
    monkeypatch.setattr(model, "train_and_predict", lambda mid, df, model_dir=None: 10.0)
    monkeypatch.setattr(
        model,
        "recommend_product_mix",
        lambda db, mid, pred: [
            {
                "product_code": "P001",
                "product_name": "Prod1",
                "recommended_quantity": 5,
            }
        ],
    )
    monkeypatch.setattr(model, "update_performance_log", lambda a, b: None)

    model.run_all_category_predictions(sales_db)

    prediction_db = tmp_path / "category_predictions_sales.db"
    assert prediction_db.exists()
    with sqlite3.connect(prediction_db) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT mid_code, predicted_sales FROM category_predictions"
        )
        rows = cur.fetchall()
        assert rows == [("001", 10.0)]
        cur.execute(
            "SELECT product_code, recommended_quantity FROM category_prediction_items"
        )
        items = cur.fetchall()
        assert items == [("P001", 5)]


def test_run_for_db_paths_with_tuning(tmp_path, monkeypatch):
    sales_db = tmp_path / "sales.db"
    init_db(sales_db)
    with sqlite3.connect(sales_db) as conn:
        conn.execute(
            """
            INSERT INTO mid_sales (
                collected_at, mid_code, mid_name, product_code, product_name, sales,
                order_cnt, purchase, disposal, stock, soldout, weekday, month, week_of_year,
                is_holiday, temperature, rainfall
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2024-01-01 00:00:00",
                "001",
                "Cat1",
                "P001",
                "Prod1",
                5,
                0,
                0,
                0,
                0,
                0,
                0,
                1,
                1,
                0,
                20.0,
                0.0,
            ),
        )
        conn.execute(
            """
            INSERT INTO mid_sales (
                collected_at, mid_code, mid_name, product_code, product_name, sales,
                order_cnt, purchase, disposal, stock, soldout, weekday, month, week_of_year,
                is_holiday, temperature, rainfall
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "2024-01-01 00:00:00",
                "002",
                "Cat2",
                "P002",
                "Prod2",
                3,
                0,
                0,
                0,
                0,
                0,
                0,
                1,
                1,
                0,
                20.0,
                0.0,
            ),
        )
        conn.commit()

    def fake_get_training_data_for_category(db, mid):
        return pd.DataFrame(
            {
                "date": [datetime(2024, 1, 1).date()],
                "total_sales": [1],
                "total_purchase": [1],
                "total_disposal": [0],
                "total_soldout": [0],
                "total_stock": [10],
                "is_stockout": [0],
                "weekday": [0],
                "month": [1],
                "week_of_year": [1],
                "is_holiday": [0],
                "true_demand": [1],
                "disposal_ratio": [0.0],
                "demand_gap": [0],
                "shelf_life_days": [0],
            }
        )

    def fake_get_weather_data(dates):
        return pd.DataFrame(
            {
                "date": [datetime(2024, 1, 1).date()],
                "temperature": [20.0],
                "rainfall": [0.0],
            }
        )

    call_order = []

    def fake_tune_model(mid, df, output_dir, prediction_db_path, error_threshold):
        call_order.append(mid)
        if mid == "002":
            raise ValueError("fail")

    monkeypatch.setattr(model, "update_performance_log", lambda a, b: None)
    import prediction.main as pred_main

    monkeypatch.setattr(
        pred_main, "get_training_data_for_category", fake_get_training_data_for_category
    )
    monkeypatch.setattr(pred_main, "get_weather_data", fake_get_weather_data)
    monkeypatch.setattr(pred_main, "tune_model", fake_tune_model)
    monkeypatch.setattr(pred_main, "run_all_category_predictions", lambda db: None)
    pred_main.run_for_db_paths([sales_db], tune=True, model_dir=tmp_path)

    assert call_order == ["001", "002"]


def test_recommend_product_mix_filters_stockouts(tmp_path):
    db_path = tmp_path / "sales.db"
    init_db(db_path)

    today = datetime.now().date()
    rows = []
    for i in range(7):
        date = today - timedelta(days=6 - i)
        base = [
            f"{date} 00:00:00",
            "001",
            "Cat1",
            "",
            "",
            1,
            0,
            0,
            0,
            0,
            0,
            date.weekday(),
            date.month,
            date.isocalendar()[1],
            0,
            20.0,
            0.0,
        ]
        p1 = base.copy()
        p1[3] = "P001"
        p1[4] = "Prod1"
        p1[9] = 0 if i < 5 else 10
        rows.append(tuple(p1))
        p2 = base.copy()
        p2[3] = "P002"
        p2[4] = "Prod2"
        p2[9] = 10
        rows.append(tuple(p2))

    insert_sql = """
        INSERT INTO mid_sales (
            collected_at, mid_code, mid_name, product_code, product_name, sales,
            order_cnt, purchase, disposal, stock, soldout, weekday, month, week_of_year,
            is_holiday, temperature, rainfall
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with sqlite3.connect(db_path) as conn:
        conn.executemany(insert_sql, rows)
        conn.commit()

    recs = recommend_product_mix(db_path, "001", 10)
    codes = [r["product_code"] for r in recs]
    assert "P001" not in codes
    assert "P002" in codes
    assert all("stockout_rate" in r for r in recs)
