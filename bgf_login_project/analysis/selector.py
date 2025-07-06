import json
from pathlib import Path

SELECTOR_FILE = Path(__file__).resolve().parent / "selector.json"

with open(SELECTOR_FILE, "r", encoding="utf-8") as f:
    SELECTORS: dict[str, str] = json.load(f)
