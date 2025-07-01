from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time


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
) -> None:
    """Move focus down the grid using ArrowDown and scroll when needed."""
    with open(log_path, "w", encoding="utf-8") as log:
        def write_log(msg: str) -> None:
            ts = time.strftime("%H:%M:%S")
            log.write(f"[{ts}] {msg}\n")
            log.flush()
            print(f"[{ts}] {msg}")

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
            driver.execute_script("arguments[0].focus();", first_cell)
            time.sleep(0.5)
            prev_id = get_active_id()
            write_log(f"• 초기 포커스: {prev_id}")
        except Exception as e:
            write_log(f"❌ 초기 셀 포커스 실패: {e}")
            return

        for i in range(max_steps):
            action.send_keys(Keys.ARROW_DOWN).perform()
            time.sleep(0.3)
            curr_id = get_active_id()

            if not curr_id:
                write_log(f"[{i}] ⚠ activeElement 없음 → 중단")
                break

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
