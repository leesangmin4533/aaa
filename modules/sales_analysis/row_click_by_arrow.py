from __future__ import annotations

import re
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from log_util import create_logger

MODULE_NAME = "row_click_arrow"
log = create_logger(MODULE_NAME)


def row_click_by_arrow(
    driver,
    start_cell_id: str,
    text_suffix: str = ":text",
    delay: float = 0.5,
    max_repeat: int = 3,
    max_steps: int = 100,
) -> None:
    """Move down the grid via ArrowDown and click cells matching a numeric text.

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver instance.
    start_cell_id : str
        ID of the first grid cell to focus before moving.
    text_suffix : str, optional
        Suffix used to locate the text element for each row.
    delay : float, optional
        Pause between key presses.
    max_repeat : int, optional
        Stop when the same cell is focused this many times in a row.
    max_steps : int, optional
        Maximum iterations before aborting.
    """

    base_prefix = start_cell_id.split("gridrow_")[0] + "gridrow_"
    try:
        start_cell = driver.find_element(By.ID, start_cell_id)
        ActionChains(driver).move_to_element(start_cell).click().perform()
        driver.execute_script("arguments[0].focus();", start_cell)
    except Exception as e:
        log("start", "오류", f"초기 셀 클릭 실패: {e}")
        return

    action = ActionChains(driver)
    prev_id = None
    repeat = 0

    for _ in range(max_steps):
        active = driver.switch_to.active_element
        cell_id = active.get_attribute("id") or ""

        if cell_id == prev_id:
            repeat += 1
            if repeat >= max_repeat:
                log("loop", "완료", f"동일 셀 {repeat}회 반복 → 종료")
                break
        else:
            repeat = 0

        m = re.search(r"gridrow_(\d+)", cell_id)
        if not m:
            action.send_keys(Keys.ARROW_DOWN).perform()
            time.sleep(delay)
            prev_id = cell_id
            continue

        row_idx = m.group(1)
        text_id = f"{base_prefix}{row_idx}.cell_{row_idx}_0{text_suffix}"
        try:
            text_elem = driver.find_element(By.ID, text_id)
            text = text_elem.text.strip()
        except Exception:
            action.send_keys(Keys.ARROW_DOWN).perform()
            time.sleep(delay)
            prev_id = cell_id
            continue

        if text.isdigit() and 1 <= int(text) <= 900:
            real_cell_id = f"{base_prefix}{row_idx}.cell_{row_idx}_0"
            try:
                driver.find_element(By.ID, real_cell_id).click()
                log("click", "완료", f"{real_cell_id} 클릭")
            except Exception as e:
                log("click", "오류", f"{real_cell_id} 클릭 실패: {e}")
        else:
            log("skip", "실행", f"조건 불일치: '{text}'")

        action.send_keys(Keys.ARROW_DOWN).perform()
        time.sleep(delay)
        prev_id = cell_id

