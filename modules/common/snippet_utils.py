import json
import sys
from pathlib import Path


def load_snippet_ids(path: str) -> list[str]:
    """Load the id list from a snippet JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("id목록") or data.get("ids") or []


def parse_id_entry(entry: str) -> tuple[str, str | None]:
    """Split an entry like 'edt_id:input' into (id, tag)."""
    if ":" in entry:
        elem_id, tag = entry.split(":", 1)
    else:
        elem_id, tag = entry, None
    return elem_id, tag


def generate_simple_steps(ids: list[str]) -> list[dict]:
    """Generate steps with optional click for button tags."""
    steps = []
    for entry in ids:
        elem_id, tag = parse_id_entry(entry)
        alias = elem_id
        steps.append({
            "action": "find_element",
            "by": "xpath",
            "value": f"//*[@id='{elem_id}']",
            "as": alias,
        })
        if tag == "button":
            steps.append({
                "action": "click",
                "target": alias,
                "log": f"✅ {alias} 클릭",
            })
    return steps


def generate_command_steps(ids: list[str]) -> list[dict]:
    """Generate steps using simple prefix rules."""
    steps = []
    for entry in ids:
        elem_id = entry.split(":", 1)[0]
        alias = elem_id
        steps.append({
            "action": "find_element",
            "by": "xpath",
            "value": f"//*[@id='{elem_id}']",
            "as": alias,
        })
        if elem_id.startswith("btn_"):
            steps.append({
                "action": "click",
                "target": alias,
                "log": f"✅ {alias} 클릭",
            })
        elif elem_id.startswith("edt_") or elem_id.startswith("txt_"):
            steps.append({
                "action": "send_keys",
                "target": alias,
                "keys": "",
                "log": f"✅ {alias} 입력",
            })
    return steps


def save_steps(steps: list[dict], output_path: str) -> None:
    Path(output_path).write_text(
        json.dumps({"steps": steps}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


CLI_USAGE = (
    "Usage: python -m modules.common.snippet_utils <mode> <input.json> <output.json>\n"
    "mode: 'json' for simple conversion, 'command' for prefix rules"
)


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 3 or argv[0] not in {"json", "command"}:
        print(CLI_USAGE)
        sys.exit(1)

    mode, input_path, output_path = argv
    ids = load_snippet_ids(input_path)
    if mode == "json":
        steps = generate_simple_steps(ids)
    else:
        steps = generate_command_steps(ids)
    save_steps(steps, output_path)


if __name__ == "__main__":
    main()
