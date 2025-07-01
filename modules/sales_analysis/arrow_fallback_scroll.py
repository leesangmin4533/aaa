from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import re

from .grid_click_logger import log_detail


def scroll_with_arrow_fallback_loop(
    driver,
    max_steps: int = 100,
    scroll_xpath: str = (
        "//*[@id=\"mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm.form.div2.form.gdList.vscrollbar.incbutton:icontext\"]"
    ),
    start_cell_id: str = (
        "mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm.form.div2.form.gdList.body.gridrow_0.cell_0_0"
    ),
    log_path: str = "grid_click_log.txt",
    row_start: int = 0,
    row_end: int | None = None,
) -> None:
    """Move focus down the grid using ArrowDown and scroll when needed.

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver instance.
    max_steps : int, optional
        Maximum loop iterations.
    scroll_xpath : str, optional
        XPath of the scroll button.
    start_cell_id : str, optional
        ID of the starting cell.
    log_path : str, optional
        Path of the log file.
    row_start : int, optional
        Index of the first row to allow clicking.
    row_end : int | None, optional
        Last row index to allow. ``None`` means no upper bound.
    """
    # reset log file
    open(log_path, "w", encoding="utf-8").close()

    def write_log(msg: str) -> None:
        log_detail(msg, log_path=log_path)

    def get_active_id():
        try:
            return driver.execute_script("return document.activeElement?.id")
        except Exception:
            return None

    write_log("▶ 실행: 방향키 기반 셀 이동 시작")
    action = ActionChains(driver)

    try:
        first_cell = driver.find_element(By.ID, start_cell_id)
        ActionChains(driver).move_to_element(first_cell).click().perform()
        time.sleep(0.5)
        prev_id = get_active_id()
        write_log(f"• 초기 포커스: {prev_id}")
    except Exception as e:
        write_log(f"❌ 초기 셀 포커스 실패: {e}")
        return

    for i in range(max_steps):
        action.send_keys(Keys.ARROW_DOWN).perform()
        write_log(f"[{i}] ↓ ArrowDown")
        time.sleep(1)
        curr_id = get_active_id()
        write_log(f"[{i}] activeElement → {curr_id}")

        if not curr_id:
            write_log(f"[{i}] ⚠ activeElement 없음 → 중단")
            break

        match = re.search(r"gridrow_(\d+)\.cell_", curr_id or "")
        row_idx = int(match.group(1)) if match else None

        if (
            row_idx is None
            or row_idx < row_start
            or (row_end is not None and row_idx > row_end)
            or not curr_id.endswith("_0_0")
        ):
            write_log(f"[{i}] ⚠ 포커스 필터 미통과: {curr_id}")
            prev_id = curr_id
            continue

        if curr_id == prev_id:
            try:
                scroll_btn = driver.find_element(By.XPATH, scroll_xpath)
                scroll_btn.click()
                write_log(f"[{i}] ⬇ 스크롤 버튼 클릭 (포커스 유지 중: {curr_id})")
                time.sleep(0.5)
                continue
            except Exception as e:
                write_log(f"[{i}] ❌ 스크롤 실패: {e}")
                break

        try:
            cell = driver.find_element(By.ID, curr_id)
            text = cell.text.strip()
            write_log(f"[{i}] ✅ 셀 클릭: ID={curr_id}, 텍스트='{text}'")
            cell.click()
        except Exception as e:
            write_log(f"[{i}] ❌ 셀 클릭 실패: ID={curr_id}, 오류: {e}")
            break

        prev_id = curr_id

    write_log("✅ 완료: 방향키 기반 셀 이동 종료")
