from pathlib import Path
from dotenv import load_dotenv
import os
import google.generativeai as genai
from log_util import create_logger

MODULE_NAME = "gemini_query"

log = create_logger(MODULE_NAME)


def load_api_key() -> str:
    """Load the Gemini API key from the environment."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not found in environment")
    genai.configure(api_key=api_key)
    return api_key


def ask_gemini(question: str, model: str = "models/gemini-1.5-flash") -> str:
    """Send a single question to the Gemini model and return the response text."""
    load_api_key()
    model = genai.GenerativeModel(model)
    response = model.generate_content(question)
    return response.text.strip()


def ask_from_file(question_file: str) -> list[tuple[str, str]]:
    """Read questions from a file and return a list of (question, answer) pairs."""
    lines = [l.strip() for l in Path(question_file).read_text(encoding="utf-8").splitlines()]
    questions = [q for q in lines if q]
    qa_pairs = []
    for q in questions:
        try:
            answer = ask_gemini(q)
            qa_pairs.append((q, answer))
            log("ask", "완료", f"{q} → {answer[:30]}...")
        except Exception as e:
            log("ask", "오류", f"{q} → {e}")
    return qa_pairs


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ask questions from a file using Gemini")
    parser.add_argument("input", help="Path to text file with one question per line")
    parser.add_argument("--output", help="Optional path to save Q/A pairs as JSON")
    args = parser.parse_args()

    pairs = ask_from_file(args.input)
    if args.output:
        import json
        Path(args.output).write_text(json.dumps(pairs, ensure_ascii=False, indent=2), encoding="utf-8")
    for q, a in pairs:
        print(f"Q: {q}\nA: {a}\n")
