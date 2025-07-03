from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from log_util import create_logger

MODULE_NAME = "cell_filter_logger"
log = create_logger(MODULE_NAME)


def click_cells_log_filter(driver, filter_value: str, max_cells: int = 100) -> None:
    """Click cells sequentially and log when a cell text matches a filter.

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver instance.
    filter_value : str
        Text value to search for in each cell.
    max_cells : int, optional
        Maximum number of cells to iterate over.
    """
    base_id = (
        "mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm"
        ".form.div2.form.gdList.body"
    )

    for idx in range(max_cells):
        cell_id = f"{base_id}.gridrow_{idx}.cell_{idx}_0"
        try:
            cell = driver.find_element(By.ID, cell_id)
            text = cell.text.strip()
            if filter_value in text:
                log("filter", "성공", f"[{idx}] 필터 '{filter_value}' 발견: {text}")
            else:
                log("filter", "실행", f"[{idx}] 필터 미일치: {text}")
            cell.click()
        except NoSuchElementException:
            log("click", "완료", f"[{idx}] 셀 미존재 → 종료")
            break

