from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
from log_util import create_logger

MODULE_NAME = "mid_click"

log = create_logger(MODULE_NAME)

# XPath for the grid's vertical scrollbar trackbar
TRACKBAR_XPATH = (
    "//*[@id='mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm.form.div2.form.gdList.vscrollbar.trackbar']"
)


def scroll_to_expand_dom(driver, scroll_delay: float = 0.2, max_scrolls: int = 200) -> None:
    """Scroll the grid's trackbar to ensure all code cells are loaded into the DOM."""

    trackbar = driver.find_element(By.XPATH, TRACKBAR_XPATH)
    actions = ActionChains(driver)

    for _ in range(max_scrolls):
        actions.click_and_hold(trackbar).move_by_offset(0, 5).release().perform()
        time.sleep(scroll_delay)


def collect_all_code_cells(driver, scroll_delay: float = 0.2, max_scrolls: int = 200):
    """Return a mapping of code numbers to cell elements by scrolling the grid."""

    trackbar = driver.find_element(By.XPATH, TRACKBAR_XPATH)
    actions = ActionChains(driver)

    seen_ids = set()
    collected = {}

    for _ in range(max_scrolls):
        cells = driver.find_elements(
            By.XPATH,
            "//div[contains(@id,'gdList.body.gridrow_') and contains(@id,'cell_') and contains(@id,'_0:text')]",
        )
        for cell in cells:
            cell_id = cell.get_attribute("id")
            if not cell_id or cell_id in seen_ids:
                continue
            seen_ids.add(cell_id)
            code = cell.text.strip()
            if code.isdigit():
                num = int(code)
                if 1 <= num <= 900:
                    collected[num] = cell

        actions.click_and_hold(trackbar).move_by_offset(0, 5).release().perform()
        time.sleep(scroll_delay)

    return collected


def try_or_none(func):
    """Return the result of ``func`` or ``None`` if it raises."""
    try:
        return func()
    except Exception:
        return None


def click_codes_in_order(driver, start: int = 1, end: int = 900) -> None:
    """Click mid-category grid rows in numerical order from ``start`` to ``end``."""

    code_map = {}
    valid_codes = []

    gridrows = driver.find_elements(By.XPATH, "//div[contains(@id, 'gdList.body.gridrow')]")
    log("scan_row", "실행", f"총 행 수: {len(gridrows)}")

    for row in gridrows:
        try:
            row_id = row.get_attribute("id")
            if not row_id:
                continue
            cell = driver.find_element(By.ID, f"{row_id}:text")
            code = cell.text.strip()

            if code.isdigit():
                num = int(code)
                if start <= num <= end:
                    code_map[num] = cell
                    valid_codes.append(f"{num:03d}")
        except Exception:
            continue  # 무시하고 다음 행으로

    if valid_codes:
        log("scan_row", "실행", f"유효 코드 {len(valid_codes)}건 추출됨: {', '.join(valid_codes)}")
    else:
        log("scan_row", "실행", "유효 코드 없음")

    click_success = 0
    not_found_count = 0

    for num in range(start, end + 1):
        cell = code_map.get(num)
        if cell:
            try:
                log("click_code", "실행", f"코드 {num:03d} 클릭 중...")
                try:
                    overlay = driver.find_element(By.ID, "nexacontainer")
                    if overlay.is_displayed():
                        WebDriverWait(driver, 5).until_not(
                            EC.presence_of_element_located((By.ID, "nexacontainer"))
                        )
                except Exception:
                    pass

                try:
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable(cell)).click()
                except Exception:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cell)
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable(cell)).click()

                click_success += 1
                time.sleep(1.0)
            except Exception as e:  # pragma: no cover - unexpected selenium errors
                import traceback
                import io

                tb_io = io.StringIO()
                traceback.print_exc(file=tb_io)
                trace = tb_io.getvalue().strip()

                log("click_code", "디버그", f"셀 ID: {cell.get_attribute('id')}")
                log(
                    "click_code",
                    "디버그",
                    f"셀 표시 여부: {cell.is_displayed()}, 활성 여부: {cell.is_enabled()}"
                )
                log("click_code", "오류", f"코드 {num:03d} 클릭 실패: {repr(e)}\n{trace}")
        else:
            not_found_count += 1

    total = end - start + 1
    log("click_code", "실행", f"전체 {total} 중 클릭 성공 {click_success}건, 없음 {not_found_count}건")


def click_codes_by_arrow(
    driver,
    delay: float = 1.0,
    max_retry: int = 3,
) -> None:
    """Click mid-category codes by scanning and sorting cell IDs."""

    cells = driver.find_elements(By.XPATH, "//div[contains(@id,'gdList.body.gridrow')]")

    entries = []
    for cell in cells:
        cid = cell.get_attribute("id") or ""
        if not cid.endswith("_0:text"):
            continue
        code = cell.text.strip()
        if code.isdigit():
            num = int(code)
            if 1 <= num <= 900:
                entries.append((num, cell))

    entries.sort(key=lambda x: x[0])

    code_counts = {}
    last_code = ""
    last_cell_id = ""

    for num, cell in entries:
        code_str = f"{num:03d}"
        attempts = 0
        success = False
        while attempts < max_retry:
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    cell,
                )
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable(cell)).click()
                success = True
                break
            except Exception as e:
                attempts += 1
                log("click_code", "오류", f"코드 {code_str} 클릭 실패 {attempts}회: {e}")
                time.sleep(delay)

        if not success:
            last_code = code_str
            last_cell_id = cell.get_attribute("id") or ""
            log("click_code", "종료", f"코드 {code_str} 클릭 실패 → 루프 종료")
            break

        last_code = code_str
        last_cell_id = cell.get_attribute("id") or ""
        code_counts[code_str] = code_counts.get(code_str, 0) + 1
        log("click_code", "실행", f"코드 {code_str} 클릭")
        time.sleep(delay)

        if code_counts[code_str] >= 3:
            log("click_code", "종료", f"코드 {code_str} 3회 이상 등장 → 종료")
            break

    total_clicks = sum(code_counts.values())
    log("click_code", "완료", f"총 클릭: {total_clicks}건")
    log(
        "click_code",
        "최종 종료",
        {
            "마지막 코드": last_code,
            "마지막 셀 ID": last_cell_id,
            "코드 누적": code_counts,
        },
    )


def click_all_codes_after_scroll(driver) -> None:
    """Scroll the grid to collect all code cells and click them sequentially."""
    try:
        scroll_to_expand_dom(driver)
    except Exception as e:  # pragma: no cover - best effort scrolling
        log("scroll", "오류", f"스크롤 실패: {e}")

    collected = collect_all_code_cells(driver, max_scrolls=1)
    entries = sorted(collected.items())

    code_counts = {}
    last_code = ""
    last_cell_id = ""

    for num, cell in entries:
        code_str = f"{num:03d}"
        success = False

        for _ in range(3):
            try:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    cell,
                )
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable(cell)).click()
                success = True
                break
            except Exception as e:
                log("click_code", "오류", f"코드 {code_str} 클릭 실패: {e}")
                time.sleep(0.5)

        if not success:
            log("click_code", "종료", f"코드 {code_str} 클릭 실패 → 루프 종료")
            break

        code_counts[code_str] = code_counts.get(code_str, 0) + 1
        last_code, last_cell_id = code_str, cell.get_attribute("id")

        log("click_code", "실행", f"코드 {code_str} 클릭")
        time.sleep(1.0)

        if code_counts[code_str] >= 3:
            log("click_code", "종료", f"코드 {code_str} 3회 이상 등장 → 종료")
            break

    log("click_code", "완료", f"총 클릭: {sum(code_counts.values())}건")
    log(
        "click_code",
        "최종 종료",
        {
            "마지막 코드": last_code,
            "마지막 셀 ID": last_cell_id,
            "코드 누적": code_counts,
        },
    )
