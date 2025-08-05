import io
import logging
import pathlib
import sys
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from data_collector import collect_and_save


def test_collect_and_save_init_db_when_no_data(tmp_path):
    db_path = tmp_path / "test.db"
    driver = object()

    stream = io.StringIO()
    test_logger = logging.getLogger("test_logger")
    test_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(stream)
    test_logger.addHandler(handler)

    with patch("data_collector.execute_collect_single_day_data", return_value={"success": False, "data": None}), \
         patch("data_collector.get_missing_past_dates", return_value=[]), \
         patch("data_collector.init_db") as mock_init_db, \
         patch("data_collector.get_logger", return_value=test_logger):
        result = collect_and_save(driver, db_path, "test_store")

    mock_init_db.assert_called_once_with(db_path)
    assert result is False
    logs = stream.getvalue()
    assert "mid_sales table initialized but no data collected" in logs

    test_logger.removeHandler(handler)
