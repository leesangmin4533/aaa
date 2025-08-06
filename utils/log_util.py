from typing import Union
import logging
import os
import json
from datetime import datetime
from pathlib import Path


# 프로젝트 루트 경로
ROOT_DIR = Path(__file__).resolve().parents[1]


class JsonFormatter(logging.Formatter):
    """로그 레코드를 JSON 문자열로 변환합니다."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - short description
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "tag": getattr(record, "tag", "system"),
            "store_id": getattr(record, "store_id", None),
        }
        if record.exc_info:
            log_record["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_record, ensure_ascii=False)


class TagFilter(logging.Filter):
    """Ensure log records have a ``tag`` attribute."""

    def __init__(self, default_tag: str = "system") -> None:
        super().__init__()
        self.default_tag = default_tag

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - short description
        if not hasattr(record, "tag"):
            record.tag = self.default_tag
        return True


class StoreLoggerAdapter(logging.LoggerAdapter):
    """store_id 필드를 기본으로 제공하는 LoggerAdapter."""

    def __init__(self, logger: logging.Logger, store_id: str) -> None:
        super().__init__(logger, {"store_id": store_id})

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:  # noqa: D401 - short description
        extra = kwargs.setdefault("extra", {})
        extra.setdefault("store_id", self.extra["store_id"])
        return msg, kwargs


def _get_log_path() -> Path:
    """Return log file path from environment or config.json."""
    env_path = os.environ.get("LOG_FILE")
    if env_path:
        p = Path(env_path).expanduser()
        return p if p.is_absolute() else ROOT_DIR / p

    config_path = ROOT_DIR / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                conf = json.load(f)
            log_file = conf.get("log_file")
            if log_file:
                path = Path(log_file)
                return path if path.is_absolute() else ROOT_DIR / path
        except Exception:
            pass

    return ROOT_DIR / "logs" / "automation.log"


def _setup_logger(name: str, level: int = logging.INFO, default_tag: str = "system") -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    fmt = JsonFormatter()
    tag_filter = TagFilter(default_tag)

    stream_handler = logging.StreamHandler()
    stream_handler.addFilter(tag_filter)
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(level)
    logger.addHandler(stream_handler)

    if os.environ.get("LOG_TO_MEMORY"):
        from io import StringIO

        mem_stream = StringIO()
        mem_handler = logging.StreamHandler(mem_stream)
        mem_handler.setFormatter(fmt)
        logger.addHandler(mem_handler)
        mem_handler.addFilter(tag_filter)
        logger._memory_stream = mem_stream  # type: ignore[attr-defined]
    else:
        log_path = _get_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        file_handler.setFormatter(fmt)
        file_handler.addFilter(tag_filter)
        file_handler.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
    return logger


def get_logger(
    name: str,
    *,
    level: int = logging.INFO,
    default_tag: str = "system",
    store_id: Union[str, None] = None,
) -> logging.Logger:
    """로거를 생성하거나 가져옵니다."""

    logger = _setup_logger(name, level, default_tag)

    if store_id is not None:
        adapter: logging.Logger = StoreLoggerAdapter(logger, store_id)
    else:
        adapter = logger

    adapter.debug(
        f"Logger '{name}' initialized", extra={"tag": default_tag, "store_id": store_id}
    )

    return adapter