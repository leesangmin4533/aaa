from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
import re

from .grid_click_logger import log_detail


def find_cell_under_mainframe(driver, depth: int = 3):
    """Return the grid cell element under the current active element.

    If the active element itself is a cell, it is returned immediately. Otherwise
    the DOM tree under the active element is searched breadth-first for an
    element whose ID contains ``gridrow_`` and ``cell``.

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver instance.
    depth : int, optional
        Max DOM depth to search.
    """
    script = f"""
        function findCell() {{
            var elem = document.activeElement;
            if (elem && elem.id && elem.id.includes('gridrow_') && elem.id.includes('cell')) {{
                return elem;
            }}
            function findCellUnder(e, maxDepth) {{
                if (!e || maxDepth <= 0) return null;
                let queue = [e];
                while (queue.length) {{
                    const current = queue.shift();
                    if (current.id && current.id.includes('gridrow_') && current.id.includes('cell')) {{
                        return current;
                    }}
                    for (const child of current.children || []) {{
                        queue.push(child);
                    }}
                }}
                return null;
            }}
            return findCellUnder(elem, {depth});
        }}
        return findCell();
    """
    return driver.execute_script(script)


def scroll_with_arrow_fallback_loop(
    driver,
    max_steps: int = 100,
    start_cell_id: str = (
        "mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm.form.div2.form.gdList.body.gridrow_0.cell_0_0"
    ),
    log_path: str = "grid_click_log.txt",
) -> None:
    """Move focus down the grid using ArrowDown and click the current row.

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver instance.
    max_steps : int, optional
        Maximum loop iterations.
    start_cell_id : str, optional
        ID of the starting cell.
    log_path : str, optional
        Path of the log file.
    """
    # reset log file
    open(log_path, "w", encoding="utf-8").close()

    base_prefix = start_cell_id.split("gridrow_")[0] + "gridrow_"

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
        time.sleep(2)
        cell_elem = find_cell_under_mainframe(driver)
        if isinstance(cell_elem, str):
            curr_id = cell_elem
        elif cell_elem is not None:
            curr_id = cell_elem.get_attribute("id")
        else:
            curr_id = get_active_id()

        write_log(f"[{i}] 찾은 셀 ID → {curr_id}")

        if not curr_id:
            write_log(f"[{i}] ⚠ activeElement 없음 → 중단")
            break


        match = re.search(r"gridrow_(\d+)", curr_id or "")
        row_idx = int(match.group(1)) if match else None
        if row_idx is None:
            curr_xpath = f"//*[@id='{curr_id}']" if curr_id else "N/A"
            write_log(f"[{i}] ⚠ 셀 ID 파싱 실패: {curr_id} (xpath={curr_xpath})")
            prev_id = curr_id
            continue

        text_cell_id = f"{base_prefix}{row_idx}.cell_{row_idx}_0:text"
        try:
            cell = driver.find_element(By.ID, text_cell_id)
            text = cell.text.strip()
            write_log(f"[{i}] 셀 확인: ID={text_cell_id}, 텍스트='{text}'")
            if text.isdigit() and 1 <= int(text) <= 900:
                cell.click()
                write_log(f"[{i}] ✅ 셀 클릭 완료")
            else:
                write_log(f"[{i}] ⚠ 클릭 건너뜀: 텍스트 '{text}'")
        except Exception as e:
            text_xpath = f"//*[@id='{text_cell_id}']"
            write_log(
                f"[{i}] ❌ 셀 클릭 실패: ID={text_cell_id}, xpath={text_xpath}, 오류: {e}"
            )
            break

        prev_id = curr_id

    write_log("✅ 완료: 방향키 기반 셀 이동 종료")
