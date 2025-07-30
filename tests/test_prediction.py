import importlib.util
import pathlib
from unittest.mock import patch

db_util_spec = importlib.util.spec_from_file_location(
    "db_util", pathlib.Path(__file__).resolve().parents[1] / "utils" / "db_util.py"
)
db_util = importlib.util.module_from_spec(db_util_spec)
db_util_spec.loader.exec_module(db_util)


def test_run_jumeokbap_prediction_creates_db(tmp_path, monkeypatch):
    sales_db = tmp_path / "sales.db"
    jumeok_db = tmp_path / "jumeok.db"

    monkeypatch.setattr(db_util, "get_configured_db_path", lambda: sales_db)
    monkeypatch.setattr(db_util, "JUMEOKBAP_DB_PATH", jumeok_db, raising=False)
    monkeypatch.setattr(db_util, "predict_jumeokbap_quantity", lambda p: 1.0)
    monkeypatch.setattr(db_util, "recommend_product_mix", lambda p, q: {})

    db_util.run_jumeokbap_prediction_and_save()

    assert sales_db.exists()
    assert jumeok_db.exists()
