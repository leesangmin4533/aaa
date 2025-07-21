from __future__ import annotations

from pathlib import Path
from typing import Iterable


def append_unique_lines(file_path: str | Path, lines: Iterable[str]) -> int:
    """Append unique lines to a file.

    Parameters
    ----------
    file_path : str | Path
        Target text file.
    lines : Iterable[str]
        Lines to append.
    Returns
    -------
    int
        Number of lines actually appended.
    """
    path = Path(file_path)
    existing: set[str] = set()
    if path.exists():
        existing = set(path.read_text(encoding="utf-8").splitlines())
    new_lines = [line.rstrip("\n") for line in lines if line.rstrip("\n") not in existing]
    if not path.parent.exists():
        path.parent.mkdir(parents=True)
    with path.open("a", encoding="utf-8") as f:
        for line in new_lines:
            f.write(line + "\n")
    return len(new_lines)
