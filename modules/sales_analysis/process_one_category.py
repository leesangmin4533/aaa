from selenium.webdriver.common.by import By
import time

from modules.common.network import extract_ssv_from_cdp
from modules.data_parser.parse_and_save import parse_ssv, save_filtered_rows
from pathlib import Path


CATEGORY_CELL = (
    "//*[@id='mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.WorkFrame.form.grd_msg.body.gridrow_{i}.cell_{i}_0']"
)
TEXT_SUFFIX = ":text"  # 텍스트 요소 ID에 사용될 suffix


def process_one_category(driver, index: int) -> bool:
    """Handle one mid-category row with click + separate text extraction."""

    code = f"{index:03d}"
    try:
        print(f"▶ 중분류 {code} 처리 시작")
        xpath = CATEGORY_CELL.format(i=index)

        # ✅ 실제 클릭은 기능 요소에서 수행
        print(f"🟡 중분류 {code} 클릭")
        driver.find_element(By.XPATH, xpath).click()
        time.sleep(0.3)

        # ✅ 텍스트 추출은 별도
        try:
            text_xpath = xpath + TEXT_SUFFIX
            mid_text = driver.find_element(By.XPATH, text_xpath).text.strip()
            print(f"📌 중분류 텍스트: {mid_text}")
        except Exception:
            print(f"⚠ 중분류 텍스트 추출 실패 (무시하고 계속)")

        time.sleep(1.5)

        # ✅ SSV 수집 및 필터링
        ssv_path = f"output/category_{code}_detail.txt"
        extract_ssv_from_cdp(driver, keyword="selDetailSearch", save_to=ssv_path)
        if not Path(ssv_path).exists():
            raise FileNotFoundError(ssv_path)

        with open(ssv_path, "r", encoding="utf-8") as f:
            rows = parse_ssv(f.read())
        out_path = f"output/category_{code}_filtered.txt"
        save_filtered_rows(rows, out_path, filter_dict={"STOCK_QTY": "0"})

        print(f"✅ 중분류 {code} 처리 성공")
        return True
    except Exception as e:
        print(f"❌ 중분류 {code} 처리 중 예외 발생: {e}")
        return False
