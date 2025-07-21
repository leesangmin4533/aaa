import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Callable


def _setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("[%(name)s][%(tag)s][%(levelname)s] %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    if os.environ.get("LOG_TO_MEMORY"):
        from io import StringIO

        mem_stream = StringIO()
        mem_handler = logging.StreamHandler(mem_stream)
        mem_handler.setFormatter(fmt)
        logger.addHandler(mem_handler)
        logger._memory_stream = mem_stream  # type: ignore[attr-defined]
    else:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_name = "automation.log"
        file_handler = logging.FileHandler(
            log_dir / file_name, mode="w", encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    return _setup_logger(name)
