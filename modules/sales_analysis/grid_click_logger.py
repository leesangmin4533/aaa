from datetime import datetime
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
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
    """Scroll each grid cell into view and click it sequentially with detailed logs."""
    base_id = (
        "mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm"
        ".form.div2.form.gdList.body"
    )

    with open(log_path, "w", encoding="utf-8") as log:
        def write_log(msg: str) -> None:
            ts = time.strftime("%H:%M:%S")
            log.write(f"[{ts}] {msg}\n")
            print(f"[{ts}] {msg}")

        write_log(f"▶ 실행: 셀 순회 시작 (최대 {max_cells}셀)")
        action = ActionChains(driver)

        for idx in range(max_cells):
            cell_id = f"{base_id}.gridrow_{idx}.cell_0_0"
            try:
                cell = driver.find_element(By.ID, cell_id)
                active = driver.execute_script("return document.activeElement?.id")
                write_log(f"• 포커스 상태: activeElement → {active}")

                text = cell.text.strip()
                write_log(f"✅ 셀 {idx} 클릭 시도: ID={cell_id}, 텍스트='{text}'")

                cell.click()
                cell.send_keys("")  # 명시적 포커스 부여
                time.sleep(0.2)

                action.send_keys(Keys.ARROW_DOWN).perform()
                time.sleep(0.2)

                next_id = f"{base_id}.gridrow_{idx+1}.cell_0_0"
                try:
                    next_cell = driver.find_element(By.ID, next_id)
                    write_log(
                        f"➡ 이동 확인: {cell_id} → {next_id}, 텍스트='{next_cell.text.strip()}'"
                    )
                except Exception:
                    write_log(f"⚠ 이동 실패: {next_id} 찾을 수 없음")
            except Exception as e:
                write_log(f"❌ 오류: [{idx}] 셀 접근 실패: {e}")
                break

        write_log("✅ 완료: 셀 순회 종료")
