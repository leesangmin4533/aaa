from __future__ import annotations

from pathlib import Path
from typing import Iterable


def append_unique_lines(path: Path, lines: Iterable[str]) -> int:
    """Append new lines to ``path`` while skipping duplicates.

    Returns the number of lines actually appended.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing: set[str] = set()
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            existing = {line.rstrip("\n") for line in f if line.rstrip("\n")}

    added = 0
    with path.open("a", encoding="utf-8") as f:
        for line in lines:
            text = str(line).rstrip("\n")
            if not text or text in existing:
                continue
            f.write(text + "\n")
            existing.add(text)
            added += 1
    return added
