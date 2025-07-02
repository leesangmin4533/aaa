import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from log_util import create_logger


def test_create_logger_writes_file(tmp_path):
    log_file = tmp_path / "out.log"
    log = create_logger("unit", log_file=str(log_file))
    log("step", "실행", "hello")
    with open(log_file, "r", encoding="utf-8") as f:
        contents = f.read()
    assert "hello" in contents

