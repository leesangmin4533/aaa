import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gemini.query_gemini import ask_gemini, ask_from_file


def test_ask_gemini_returns_text():
    fake_model = MagicMock()
    fake_model.generate_content.return_value.text = "hello"
    with patch("gemini.query_gemini.load_api_key"), \
         patch("gemini.query_gemini.genai.GenerativeModel", return_value=fake_model):
        assert ask_gemini("hi") == "hello"


def test_ask_from_file_reads_questions(tmp_path):
    qfile = tmp_path / "q.txt"
    qfile.write_text("one\ntwo\n", encoding="utf-8")
    with patch("gemini.query_gemini.ask_gemini", side_effect=["a1", "a2"]):
        pairs = ask_from_file(str(qfile))
    assert pairs == [("one", "a1"), ("two", "a2")]
