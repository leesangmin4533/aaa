import json
import sys
from pathlib import Path


def load_snippet_ids(path):
    """Load the id list from a snippet JSON file."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data.get("id목록") or data.get("ids") or []


def generate_commands(ids):
    steps = []
    for entry in ids:
        # handle entries like "btn_search:button" by stripping tag
        elem_id = entry.split(":", 1)[0]
        alias = elem_id
        steps.append({
            "action": "find_element",
            "by": "xpath",
            "value": f"//*[@id='{elem_id}']",
            "as": alias
        })
        if elem_id.startswith("btn_"):
            steps.append({
                "action": "click",
                "target": alias,
                "log": f"✅ {alias} 클릭"
            })
        elif elem_id.startswith("edt_") or elem_id.startswith("txt_"):
            steps.append({
                "action": "send_keys",
                "target": alias,
                "keys": "",
                "log": f"✅ {alias} 입력"
            })
    return steps


def main(snippet_path, output_path):
    ids = load_snippet_ids(snippet_path)
    steps = generate_commands(ids)
    Path(output_path).write_text(
        json.dumps({"steps": steps}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python snippet_to_command.py <snippet.json> <output.json>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
