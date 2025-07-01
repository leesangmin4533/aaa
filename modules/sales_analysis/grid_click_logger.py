from datetime import datetime
import os
import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


def log_detail(message: str, log_path: str = "grid_click_log.txt") -> None:
    """Append a timestamped message to the given log file and print it."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {message}\n")
    print(f"{timestamp} {message}")


def scroll_and_click_loop(
    driver,
    max_cells: int = 100,
    log_path: str = "grid_click_log.txt",
) -> None:
    """Scroll each grid cell into view and click it sequentially."""
    if os.path.exists(log_path):
        os.remove(log_path)

    base_id = (
        "mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm"
        ".form.div2.form.gdList.body.gridrow_"
    )
    for i in range(max_cells):
        cell_id = f"{base_id}{i}.cell_0_0"
        try:
            cell = driver.find_element(By.ID, cell_id)
            driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});",
                cell,
            )
            log_detail(f"[{i}] ▶ 셀 스크롤 완료: {cell_id}", log_path)
            cell_text = cell.text
            cell.click()
            log_detail(
                f"[{i}] ✅ 클릭 완료 - 코드: '{cell_text}', ID: {cell_id}",
                log_path,
            )
            time.sleep(0.2)
        except NoSuchElementException:
            log_detail(f"[{i}] ❌ 셀 접근 실패 - ID 없음: {cell_id} → 루프 종료", log_path)
            break
