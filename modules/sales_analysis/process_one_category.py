from selenium.webdriver.common.by import By
import time

from ssv_listener import extract_ssv_from_cdp
from modules.data_parser.parse_and_save import parse_ssv, save_filtered_rows
from pathlib import Path


CATEGORY_CELL = (
    "//*[@id='mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm.form.div2.form.gdList.body.gridrow_{i}.cell_0_0']"
)


def process_one_category(driver, index: int) -> bool:
    """Handle one mid-category row.

    Parameters
    ----------
    driver : selenium.webdriver
        Active Selenium driver.
    index : int
        Row index for the mid-category grid (0-based).

    Returns
    -------
    bool
        True on success, False if any step failed.
    """
    code = f"{index:03d}"
    try:
        print(f"🟡 중분류 {code} 클릭")
        xpath = CATEGORY_CELL.format(i=index)
        driver.find_element(By.XPATH, xpath).click()
        time.sleep(0.3)
        driver.find_element(By.XPATH, xpath + ":text").click()
        time.sleep(1.5)

        ssv_path = f"output/category_{code}_detail.txt"
        extract_ssv_from_cdp(driver, keyword="selDetailSearch", save_to=ssv_path)
        if not Path(ssv_path).exists():
            raise FileNotFoundError(ssv_path)

        with open(ssv_path, "r", encoding="utf-8") as f:
            rows = parse_ssv(f.read())
        out_path = f"output/category_{code}_filtered.txt"
        save_filtered_rows(rows, out_path, filter_dict={"STOCK_QTY": "0"})
        print(f"✅ 중분류 {code} 처리 완료")
        return True
    except Exception as e:
        print(f"❌ 중분류 {code} 처리 실패: {e}")
        return False
