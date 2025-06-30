from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
from log_util import create_logger

MODULE_NAME = "navigate_mid"


log = create_logger(MODULE_NAME)


def try_or_none(func):
    """Return the result of ``func`` or ``None`` if it raises."""

    try:
        return func()
    except Exception:
        return None


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


def click_codes_by_arrow(
    driver,
    delay: float = 1.0,
    max_scrolls: int = 1000,
    retry_delay: float = 2.0,
    search_limit: int = 5,
) -> None:
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
    code_counts = {}
    last_cell_id = ""
    last_code = ""
    e = None
    missing_attempts = 0
    visited = set()
    retry_count = 0

    try:
        cell = driver.find_element(
            By.XPATH,
            "//div[contains(@id,'gdList.body.gridrow') and contains(text(),'001')]",
        )
        log("click_code", "실행", "코드 001 클릭")
        cell.click()
        first_id = cell.get_attribute("id") or ""
        last_cell_id = first_id
        last_code = "001"
        code_counts[last_code] = code_counts.get(last_code, 0) + 1
        visited.add(last_code)
        time.sleep(delay)
    except Exception:
        log("click_code", "오류", "코드 001을 찾지 못함")
        log(
            "click_code",
            "최종 종료",
            {
                "마지막 코드": last_code,
                "마지막 셀 ID": last_cell_id,
                "코드 누적": code_counts,
            },
        )
        return

    import re

    m = re.search(r"(.*gdList\.body\.gridrow_)(\d+)", first_id)
    prefix = m.group(1) if m else ""
    row_idx = int(m.group(2)) if m else 0

    for _ in range(max_scrolls):
        row_idx += 1
        actions.send_keys(Keys.ARROW_DOWN).perform()
        time.sleep(0.3)

        attempt = 0
        next_cell = None
        cell_id = f"{prefix}{row_idx}.cell_{row_idx}_0:text"

        while attempt < 2:
            found_by_id = True
            try:
                next_cell = driver.find_element(By.ID, cell_id)
            except Exception:
                found_by_id = False
                try:
                    active = driver.switch_to.active_element
                    active_id = active.get_attribute("id") or ""
                    if active_id.startswith(prefix) and active_id.endswith(":text"):
                        next_cell = active
                    else:
                        log(
                            "click_code",
                            "종료",
                            f"비정상 active_element 감지: {active_id}",
                        )
                        try:
                            log(
                                "click_code",
                                "시도",
                                f"포커스 복구: {last_cell_id}",
                            )
                            recover_cell = driver.find_element(By.ID, last_cell_id)
                            actions.move_to_element(recover_cell).click().perform()
                            time.sleep(1.0)
                            log(
                                "click_code",
                                "완료",
                                f"포커스 복구 성공: {last_cell_id}",
                            )
                            # 포커스 복구 성공 후 다음 셀도 명확히 _0:text 로 강제 지정
                            row_idx += 1
                            cell_id = f"{prefix}{row_idx}.cell_{row_idx}_0:text"
                            continue
                        except Exception as rec_err:
                            log(
                                "click_code",
                                "오류",
                                f"포커스 복구 실패: {rec_err}",
                            )
                        next_cell = driver.find_element(By.ID, cell_id)
                        found_by_id = True
                except Exception as err:
                    e = err
                    next_cell = None

            try:
                if next_cell is None:
                    raise Exception("cell missing")
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    next_cell,
                )
                next_cell.click()
                if not found_by_id:
                    raise Exception("clicked active element")
                break
            except Exception as click_err:
                attempt += 1
                if attempt >= 2:
                    log("click_code", "종료", f"셀 클릭 실패: {click_err}")
                    time.sleep(1)
                    recovery_success = False
                    try:
                        recovery = driver.find_element(By.ID, last_cell_id)
                        recovery.click()
                        recovery_success = True
                    except Exception as rec_err:
                        log("click_code", "오류", f"재클릭 실패: {rec_err}")

                    if recovery_success:
                        row_idx -= 1
                        next_cell = None
                        break

                    search_loops = 0
                    while search_loops < search_limit:
                        actions.send_keys(Keys.ARROW_DOWN).perform()
                        time.sleep(0.3)
                        search_loops += 1
                        row_idx += 1
                        tmp_id = f"{prefix}{row_idx}.cell_{row_idx}_0:text"
                        try:
                            next_cell = driver.find_element(By.ID, tmp_id)
                            cell_id = tmp_id
                            break
                        except Exception:
                            continue

                    if next_cell is None:
                        missing_attempts += 1
                        if missing_attempts >= search_limit:
                            log(
                                "click_code",
                                "종료",
                                f"예상 셀 탐색 실패 {missing_attempts}회",
                            )
                            return
                        row_idx -= 1
                    else:
                        missing_attempts = 0
                    break
                time.sleep(retry_delay)

        if not next_cell:
            continue

        last_cell_id = cell_id
        code = next_cell.text.strip()
        last_code = code

        if not code or not code.isdigit():
            continue

        if code in visited:
            retry_count += 1
            if retry_count >= 3:
                log(
                    "click_code",
                    "종료",
                    f"동일 코드 {code} 3회 시도 → 종료",
                )
                break
        else:
            retry_count = 0
            visited.add(code)

        code_counts[code] = code_counts.get(code, 0) + 1
        log("click_code", "실행", f"코드 {code} 클릭")
        time.sleep(delay)

        if code_counts[code] >= 3:
            log("click_code", "종료", f"코드 {code} 3회 이상 등장 → 종료")
            break

    total_clicks = sum(code_counts.values())
    log("click_code", "완료", f"총 클릭: {total_clicks}건")
    active = try_or_none(lambda: driver.switch_to.active_element)
    focus_id = try_or_none(lambda: active.get_attribute("id")) if active else ""
    focus_text = try_or_none(lambda: active.text.strip()) if active else ""

    log(
        "click_code",
        "최종 종료",
        {
            "마지막 코드": last_code,
            "마지막 셀 ID": last_cell_id,
            "코드 누적": {k: code_counts[k] for k in list(code_counts)[-5:]},
            "포커스": {"id": focus_id, "text": focus_text},
        },
    )
