import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "file_util", pathlib.Path(__file__).resolve().parents[1] / "utils" / "file_util.py"
)
file_util = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(file_util)


def test_append_unique_lines(tmp_path):
    f = tmp_path / "out.txt"
    f.write_text("a\nb\n", encoding="utf-8")
    added = file_util.append_unique_lines(f, ["b", "c", "a", "d"])
    assert added == 2
    assert f.read_text(encoding="utf-8") == "a\nb\nc\nd\n"
