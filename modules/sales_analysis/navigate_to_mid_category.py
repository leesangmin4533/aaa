from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
from log_util import create_logger

MODULE_NAME = "navigate_mid"


log = create_logger(MODULE_NAME)


def navigate_to_mid_category_sales(driver):
    """Navigate to the '중분류별 매출 구성' page under sales analysis."""
    log("open_menu", "실행", "매출분석 메뉴 클릭")
    driver.find_element(By.XPATH, '//*[@id="mainframe.HFrameSet00.VFrameSet00.TopFrame.form.div_topMenu.form.STMB000_M0"]').click()
    time.sleep(1)

    log("wait_mid_menu", "실행", "중분류 메뉴 등장 대기")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="mainframe.HFrameSet00.VFrameSet00.TopFrame.form.pdiv_topMenu_STMB000_M0.form.STMB011_M0"]'))
    )
    time.sleep(0.5)

    log("click_mid_sales", "실행", "중분류별 매출 구성비 클릭")
    driver.find_element(By.XPATH, '//*[@id="mainframe.HFrameSet00.VFrameSet00.TopFrame.form.pdiv_topMenu_STMB000_M0.form.STMB011_M0"]').click()
    time.sleep(2)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '//*[@id="mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.WorkFrame.form.grd_msg.body.gridrow_0.cell_0_0"]'))
    )


def click_codes_in_order(driver, start: int = 1, end: int = 900) -> None:
    """Click mid-category grid rows in numerical order from ``start`` to ``end``.

    Parameters
    ----------
    driver:
        Selenium WebDriver instance currently on the mid-category sales page.
    start:
        Starting code number to attempt clicking. Defaults to ``1``.
    end:
        Ending code number to attempt clicking. Defaults to ``900``.
    """

    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By

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
        log(
            "scan_row",
            "실행",
            f"유효 코드 {len(valid_codes)}건 추출됨: {', '.join(valid_codes)}",
        )
    else:
        log("scan_row", "실행", "유효 코드 없음")

    click_success = 0
    not_found_count = 0

    for num in range(start, end + 1):
        cell = code_map.get(num)
        if cell:
            try:
                log("click_code", "실행", f"코드 {num:03d} 클릭 중...")
                # ✅ overlay disappears before attempting click
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
                    # ✅ if not clickable, scroll into view and retry
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center'});", cell
                    )
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable(cell)).click()

                click_success += 1
                time.sleep(1.0)
            except Exception as e:
                import traceback
                import io

                tb_io = io.StringIO()
                traceback.print_exc(file=tb_io)
                trace = tb_io.getvalue().strip()

                log(
                    "click_code",
                    "디버그",
                    f"셀 ID: {cell.get_attribute('id')}"
                )
                log(
                    "click_code",
                    "디버그",
                    f"셀 표시 여부: {cell.is_displayed()}, 활성 여부: {cell.is_enabled()}"
                )
                log(
                    "click_code",
                    "오류",
                    f"코드 {num:03d} 클릭 실패: {repr(e)}\n{trace}"
                )
        else:
            not_found_count += 1

    total = end - start + 1
    log("click_code", "실행", f"전체 {total} 중 클릭 성공 {click_success}건, 없음 {not_found_count}건")


def click_codes_by_arrow(driver, delay: float = 1.0, max_scrolls: int = 1000) -> None:
    """Click mid-category codes using Arrow Down navigation.

    Workflow
    --------
    1. Locate the grid cell containing the text ``001``.
    2. Click the cell and wait ``delay`` seconds.
    3. Press the ↓ arrow key to move to the next row.
    4. Read the active cell's text and check if it was already visited.
    5. If not visited, click the cell, wait ``delay`` seconds and add the code
       to ``visited``.
    6. Stop when a duplicate code appears or ``max_scrolls`` is reached.
    7. Log the total number of clicked codes.
    """

    actions = ActionChains(driver)
    visited = set()

    try:
        cell = driver.find_element(
            By.XPATH,
            "//div[contains(@id,'gdList.body.gridrow') and contains(text(),'001')]"
        )
        log("click_code", "실행", "코드 001 클릭")
        cell.click()
        visited.add("001")
        time.sleep(delay)
    except Exception as e:
        log("click_code", "오류", "코드 001을 찾지 못함")
        return

    for _ in range(max_scrolls):
        actions.send_keys(Keys.ARROW_DOWN).perform()
        time.sleep(0.2)

        try:
            active = driver.switch_to.active_element
            active.click()  # make sure each moved row is actually clicked
            code = active.text.strip()

            if not code or not code.isdigit():
                continue

            if code in visited:
                log("click_code", "종료", f"코드 {code} 중복 → 종료")
                break

            log("click_code", "실행", f"코드 {code} 클릭")
            active.click()
            visited.add(code)
            time.sleep(delay)

        except Exception as e:
            log("click_code", "오류", f"아래 이동 클릭 실패: {e}")
            continue

    log("click_code", "완료", f"총 클릭: {len(visited)}건")
