from __future__ import annotations

import datetime
import time
from pathlib import Path
from typing import Any

from selenium.webdriver.remote.webdriver import WebDriver
from utils.log_util import create_logger


HEADER = [
    "중분류코드",
    "중분류텍스트",
    "상품코드",
    "상품명",
    "매출",
    "발주",
    "매입",
    "폐기",
    "현재고",
]


def _dispatch_click(driver: WebDriver, selector: str) -> None:
    """Dispatch mousedown, mouseup and click events for the element."""
    driver.execute_script(
        """
const el = document.querySelector(arguments[0]);
if (el) {
  const rect = el.getBoundingClientRect();
  ['mousedown', 'mouseup', 'click'].forEach(type => {
    el.dispatchEvent(new MouseEvent(type, {
      bubbles: true,
      cancelable: true,
      view: window,
      clientX: rect.left + rect.width / 2,
      clientY: rect.top + rect.height / 2
    }));
  });
}
""",
        selector,
    )


def export_product_data(driver: WebDriver, output_dir: str | Path = ".") -> Path | None:
    """Collect product info by clicking codes and save it as a text file."""
    log = create_logger("export")
    from . import parse_mix_ratio_data

    df = parse_mix_ratio_data(driver)
    if df is None:
        log("export", "ERROR", "카테고리 데이터 없음")
        return None

    rows: list[list[str]] = []

    for idx, cat in df.iterrows():
        mid_code = cat.get("code", "")
        mid_text = cat.get("name", "") or ""
        _dispatch_click(driver, f"div[id^='gdList.gridrow_{idx}'] > div[id$='.cell_{idx}_0']")
        time.sleep(0.5)

        # 상품 코드 목록 추출 (프론트엔드에서 제공하는 가정)
        try:
            product_codes: list[str] = driver.execute_script(
                "return window.__CODEX__?.productCodes || []"
            )
        except Exception as e:
            log("export", "WARNING", f"상품 코드 목록 조회 실패: {e}")
            continue

        for p_idx, p_code in enumerate(product_codes):
            _dispatch_click(driver, f"div[id^='gdDetail.gridrow_{p_idx}'] > div[id$='.cell_{p_idx}_0']")
            time.sleep(0.3)
            time.sleep(0.1)
            try:
                data: dict[str, Any] = driver.execute_script(
                    "return window.__CODEX__?.currentRow || {}"
                )
            except Exception as e:
                log("export", "WARNING", f"행 데이터 조회 실패: {e}")
                data = {}

            row = [
                mid_code,
                mid_text,
                str(data.get("상품코드") or data.get("code") or p_code),
                str(data.get("상품명") or data.get("name") or ""),
                str(data.get("매출") or data.get("sales") or ""),
                str(data.get("발주") or data.get("order") or ""),
                str(data.get("매입") or data.get("purchase") or ""),
                str(data.get("폐기") or data.get("dispose") or ""),
                str(data.get("현재고") or data.get("stock") or ""),
            ]
            rows.append(row)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = datetime.date.today().strftime("%Y%m%d.txt")
    path = output_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        f.write("\t".join(HEADER) + "\n")
        for r in rows:
            f.write("\t".join(r) + "\n")
    log("export", "INFO", f"총 {len(rows)}행 저장: {path}")
    return path
