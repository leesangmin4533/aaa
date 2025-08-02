import json
import logging
from pathlib import Path
import importlib.util


_spec = importlib.util.spec_from_file_location(
    "log_util", Path(__file__).resolve().parents[1] / "utils" / "log_util.py"
)
log_util = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(log_util)


def test_logger_respects_config_path(tmp_path, monkeypatch):
    cfg = {"log_file": "logs/test.log"}
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setattr(log_util, "ROOT_DIR", tmp_path)

    logger = log_util.get_logger("test")
    file_handler = next(h for h in logger.handlers if isinstance(h, logging.FileHandler))
    assert Path(file_handler.baseFilename) == tmp_path / "logs" / "test.log"


def test_json_logging_fields(tmp_path, monkeypatch):
    log_file = tmp_path / "out.log"
    monkeypatch.setenv("LOG_FILE", str(log_file))
    logger = log_util.get_logger("test_json", store_id="store42")
    logger.info("hello world")
    for h in logger.logger.handlers if hasattr(logger, "logger") else logger.handlers:
        h.flush()

    content = log_file.read_text(encoding="utf-8").strip().splitlines()[-1]
    data = json.loads(content)
    assert data["message"] == "hello world"
    assert data["level"] == "INFO"
    assert data["store_id"] == "store42"
    assert "timestamp" in data

