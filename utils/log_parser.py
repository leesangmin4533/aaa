import re
from typing import Iterable


def extract_tab_lines(logs: Iterable[dict]) -> list[str]:
    """Return log messages containing tab-separated text.

    Chrome 로그 메시지 형식에서 따옴표 내부의 내용을 추출해 ``\t`` 문자열을
    실제 탭 문자로 변환한다.
    """
    result: list[str] = []
    for entry in logs:
        msg = entry.get("message", "") if isinstance(entry, dict) else str(entry)
        # 따옴표 안에 \t 또는 실제 탭 문자가 포함된 패턴을 찾는다.
        m = re.search(r'"([^"\n]*(?:\\t|\t)[^"\n]*)"', msg)
        if m:
            text = m.group(1).replace("\\t", "\t")
            result.append(text)
        elif "\\t" in msg or "\t" in msg:
            result.append(msg.replace("\\t", "\t"))
    return result
