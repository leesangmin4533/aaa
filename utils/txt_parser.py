from __future__ import annotations

from pathlib import Path
from typing import Any


FIELD_ORDER = [
    "midCode",
    "midName",
    "productCode",
    "productName",
    "sales",
    "order",
    "purchase",
    "discard",
    "stock",
]


def _to_int(value: str) -> int:
    try:
        return int(str(value).replace(",", ""))
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return 0


def parse_txt(path: str | Path, encoding: str = "utf-8") -> list[dict[str, Any]]:
    """Parse a tab-delimited text file into a list of record dicts."""
    path = Path(path)
    records: list[dict[str, Any]] = []
    with path.open("r", encoding=encoding) as f:
        for line in f:
            text = line.rstrip("\n")
            if not text:
                continue
            parts = text.split("\t")
            if len(parts) < len(FIELD_ORDER):
                parts += ["" for _ in range(len(FIELD_ORDER) - len(parts))]
            record = dict(zip(FIELD_ORDER, parts[: len(FIELD_ORDER)]))
            for key in ["sales", "order", "purchase", "discard", "stock"]:
                record[key] = _to_int(record.get(key, "0"))
            records.append(record)
    return records
