import importlib.util
import pathlib

_spec = importlib.util.spec_from_file_location(
    "log_parser", pathlib.Path(__file__).resolve().parents[1] / "utils" / "log_parser.py"
)
log_parser = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(log_parser)


def test_extract_tab_lines_parses_quote_escaped_tabs():
    logs = [{"message": 'prefix "001\t33\t8800\tname\t1\t1\t\t\t0" suffix'}]
    result = log_parser.extract_tab_lines(logs)
    assert result == ["001\t33\t8800\tname\t1\t1\t\t\t0"]

