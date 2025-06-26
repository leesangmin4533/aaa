import json
import sys
from pathlib import Path


def parse_id_entry(entry):
    """Split an entry like 'edt_id:input' into (id, tag)."""
    if ':' in entry:
        elem_id, tag = entry.split(':', 1)
    else:
        elem_id, tag = entry, None
    return elem_id, tag


def generate_steps(ids):
    steps = []
    for entry in ids:
        elem_id, tag = parse_id_entry(entry)
        alias = elem_id
        steps.append({
            "action": "find_element",
            "by": "xpath",
            "value": f"//*[@id='{elem_id}']",
            "as": alias
        })
        if tag == 'button':
            steps.append({
                "action": "click",
                "target": alias,
                "log": f"✅ {alias} 클릭"
            })
    return steps


def main(input_path, output_path):
    data = json.loads(Path(input_path).read_text(encoding='utf-8'))
    ids = data.get('id목록') or data.get('ids') or []
    steps = generate_steps(ids)
    Path(output_path).write_text(json.dumps({"steps": steps}, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python snippet_to_json.py <snippet.json> <output.json>')
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
