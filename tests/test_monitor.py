import sqlite3
from datetime import datetime, timedelta
import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "monitor", pathlib.Path(__file__).resolve().parents[1] / "prediction" / "monitor.py"
)
monitor = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(monitor)


def test_load_recent_performance_returns_recent_data(tmp_path):
    db_path = tmp_path / "perf.db"
    monitor.init_performance_db(db_path)

    base_date = datetime.now().date()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        for i in range(5):
            target_date = (base_date - timedelta(days=i + 1)).strftime("%Y-%m-%d")
            cursor.execute(
                """
                INSERT INTO prediction_performance (
                    evaluation_date, target_date, mid_code,
                    predicted_sales, actual_sales, error_rate_percent
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("eval", target_date, "001", 10.0, 8.0, 25.0),
            )
        old_date = (base_date - timedelta(days=8)).strftime("%Y-%m-%d")
        cursor.execute(
            """
            INSERT INTO prediction_performance (
                evaluation_date, target_date, mid_code,
                predicted_sales, actual_sales, error_rate_percent
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("eval", old_date, "001", 10.0, 8.0, 25.0),
        )
        other_mid_date = (base_date - timedelta(days=1)).strftime("%Y-%m-%d")
        cursor.execute(
            """
            INSERT INTO prediction_performance (
                evaluation_date, target_date, mid_code,
                predicted_sales, actual_sales, error_rate_percent
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("eval", other_mid_date, "002", 10.0, 8.0, 25.0),
        )
        conn.commit()

    df = monitor.load_recent_performance(db_path, "001", days=7)
    assert len(df) == 5
    assert (df["mid_code"] == "001").all()


def test_load_recent_performance_returns_empty(tmp_path):
    db_path = tmp_path / "perf.db"
    monitor.init_performance_db(db_path)

    df = monitor.load_recent_performance(db_path, "001")
    assert df.empty
