from pathlib import Path


def parse_ssv(ssv_text):
    blocks = ssv_text.split("\x1e")
    header_line = next(line for line in blocks if "ITEM_CD" in line)
    col_names = [x.split(":")[0] for x in header_line.split("\x1f")[1:]]

    result = []
    for line in blocks:
        if line.startswith("N\x1f"):
            values = line.split("\x1f")[1:]
            row = {col: values[i] if i < len(values) else "" for i, col in enumerate(col_names)}
            result.append(row)
    return result


def save_filtered_rows(rows, path, fields=["ITEM_CD", "ITEM_NM", "STOCK_QTY"]):
    filtered = [r for r in rows if r.get("STOCK_QTY", "").strip() == "0"]
    lines = [", ".join(r.get(f, "") for f in fields) for r in filtered]

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
