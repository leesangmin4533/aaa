import json
import logging
from pathlib import Path

from utils.log_util import get_logger


def load_config() -> dict:
    """Load configuration from ``config.json`` located at the project root."""
    config_path = Path(__file__).resolve().parents[1] / "config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


config = load_config()

# Base directories
SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
CODE_OUTPUT_DIR = Path(__file__).resolve().parents[1] / "code_outputs"

# DB files
ALL_SALES_DB_FILE = config["db_file"]
# 과거 데이터를 포함해 통합 저장될 SQLite 파일명
INTEGRATED_SALES_DB_FILE = config.get("past7_db_file", "past_7days.db")

# Script file names
DEFAULT_SCRIPT = config["scripts"]["default"]
LISTENER_SCRIPT = config["scripts"]["listener"]
NAVIGATION_SCRIPT = config["scripts"]["navigation"]

# Field order and timeouts
FIELD_ORDER = config["field_order"]
DATA_COLLECTION_TIMEOUT = config["timeouts"]["data_collection"]
PAGE_LOAD_TIMEOUT = config["timeouts"]["page_load"]
CYCLE_INTERVAL = config["cycle_interval_seconds"]

# Logger for modules in this package
log = get_logger(__name__, level=logging.DEBUG)
