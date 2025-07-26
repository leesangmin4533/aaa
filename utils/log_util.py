import logging
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Callable

# 프로젝트 루트 경로
ROOT_DIR = Path(__file__).resolve().parents[1]


def _get_log_path() -> Path:
    """Return log file path defined in config.json or default."""
    config_path = ROOT_DIR / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                conf = json.load(f)
            log_file = conf.get("log_file")
            if log_file:
                path = Path(log_file)
                if not path.is_absolute():
                    return ROOT_DIR / path
                return path
        except Exception:
            pass
    return ROOT_DIR / "logs" / "automation.log"


def _setup_logger(name: str) -> logging.Logger:
    # 로거 생성 또는 가져오기
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정되어 있으면 그대로 반환
    if logger.handlers:
        return logger

    # 로거 레벨 설정
    logger.setLevel(logging.DEBUG)
    
    # 로그 메시지가 상위 로거로 전파되지 않도록 설정
    logger.propagate = False

    # 상세한 로그 형식 정의
    fmt = logging.Formatter(
        "[%(asctime)s][%(name)s][%(tag)s][%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 콘솔 출력 핸들러
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(logging.INFO)  # 콘솔에는 INFO 레벨 이상만 출력
    logger.addHandler(stream_handler)

    if os.environ.get("LOG_TO_MEMORY"):
        from io import StringIO

        mem_stream = StringIO()
        mem_handler = logging.StreamHandler(mem_stream)
        mem_handler.setFormatter(fmt)
        logger.addHandler(mem_handler)
        logger._memory_stream = mem_stream  # type: ignore[attr-defined]
    else:
        log_path = _get_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """로거를 생성하거나 가져옵니다.
    
    Args:
        name: 로거 이름
        
    Returns:
        설정된 로거 인스턴스
    """
    logger = _setup_logger(name)
    
    # 로그 초기화 표시
    logger.debug(f"Logger '{name}' initialized", extra={"tag": "system"})
    
    return logger
