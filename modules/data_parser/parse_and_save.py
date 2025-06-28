from pathlib import Path

MODULE_NAME = "parse_and_save"


def log(step: str, msg: str) -> None:
    print(f"\u25b6 [{MODULE_NAME} > {step}] {msg}")


def parse_ssv(ssv_text):
    """Parse a Nexacro SSV string into a list of row dictionaries.

    Parameters
    ----------
    ssv_text : str
        Raw SSV text captured from the network.

    Returns
    -------
    list[dict]
        Parsed rows with column names as keys.
    """

    log("parse_start", "SSV 파싱 시작")
    blocks = ssv_text.split("\x1e")
    header_line = next(line for line in blocks if "ITEM_CD" in line)
    col_names = [x.split(":")[0] for x in header_line.split("\x1f")[1:]]

    result = []
    for line in blocks:
        if line.startswith("N\x1f"):
            values = line.split("\x1f")[1:]
            row = {col: values[i] if i < len(values) else "" for i, col in enumerate(col_names)}
            result.append(row)
    log("parse_end", "SSV 파싱 완료")
    return result


def save_filtered_rows(rows, path, fields=None, filter_dict=None):
    """Save filtered rows to a text file.

    Parameters
    ----------
    rows : list[dict]
        Parsed dataset rows.
    path : str
        Output path for the filtered text file.
    fields : list[str], optional
        Column names to write, defaults to ``["ITEM_CD", "ITEM_NM", "STOCK_QTY"]``.
    filter_dict : dict[str, str], optional
        Conditions for filtering rows, where each key/value pair must match the
        corresponding column exactly.
    """

    if fields is None:
        fields = ["ITEM_CD", "ITEM_NM", "STOCK_QTY"]

    def row_matches(row):
        if not filter_dict:
            return True
        for key, value in filter_dict.items():
            if row.get(key, "").strip() != value:
                return False
        return True

    log("filter", "행 필터링")
    filtered = [r for r in rows if row_matches(r)]
    lines = [", ".join(r.get(f, "") for f in fields) for r in filtered]

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    log("save", f"필터링 결과 저장: {path}")
