from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import time
from log_util import create_logger

MODULE_NAME = "mid_click"

log = create_logger(MODULE_NAME)


def send_arrow_down_native(driver) -> None:
    """Send an ArrowDown key event using CDP so Nexacro handles it natively."""
    driver.execute_cdp_cmd(
        "Input.dispatchKeyEvent",
        {
            "type": "keyDown",
            "key": "ArrowDown",
            "code": "ArrowDown",
            "windowsVirtualKeyCode": 40,
            "nativeVirtualKeyCode": 40,
        },
    )
    time.sleep(0.1)
    driver.execute_cdp_cmd(
        "Input.dispatchKeyEvent",
        {
            "type": "keyUp",
            "key": "ArrowDown",
            "code": "ArrowDown",
            "windowsVirtualKeyCode": 40,
            "nativeVirtualKeyCode": 40,
        },
    )


def click_codes_by_arrow(
    driver,
    delay: float = 0.5,
    repeat_limit: int = 3,
    focus_retry_limit: int = 5,
    start_cell_id: str = (
        "mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm.form.div2.form.gdList.body.gridrow_0.cell_0_0"
    ),
    ) -> None:
    """Click each grid row using the down arrow key until the same code repeats.

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver instance.
    delay : float, optional
        Seconds to wait between actions.
    repeat_limit : int, optional
        Stop when the same code appears this many times in a row.
    focus_retry_limit : int, optional
        Abort if the focus remains on ``mainframe`` for this many retries.
    start_cell_id : str, optional
        ID of the first grid cell to click.
    """

    first_cell = driver.find_element(By.ID, start_cell_id)
    log("click_code", "초기포커스", f"초기 셀 찾음: {start_cell_id}")

    ActionChains(driver).move_to_element(first_cell).click().perform()
    driver.execute_script("arguments[0].focus();", first_cell)  # JS로 명시적 포커스
    time.sleep(1.0)

    rows = driver.find_elements(By.XPATH, "//*[contains(@id, 'gdList.body.gridrow_')]")
    log("click_code", "행개수확인", f"로드된 그리드 행 수: {len(rows)}")

    focused = driver.switch_to.active_element
    # 처음 포커스된 셀의 내용 추출 및 출력
    cell_id = focused.get_attribute("id") or "(ID 없음)"
    cell_text = (
        focused.text.strip() or focused.get_attribute("innerText") or "(내용 없음)"
    )
    log("click_code", "초기포커스내용", f"ID: {cell_id}, 텍스트: '{cell_text}'")
    log(
        "click_code",
        "초기포커스확인",
        f"초기 포커스된 셀 ID: {focused.get_attribute('id')}",
    )

    last_code = ""
    repeat_count = 0
    code_counts: dict[str, int] = {}
    last_cell_id = ""
    focus_retry_count = 0

    while True:
        focused = driver.switch_to.active_element
        cell_id = focused.get_attribute("id") or ""

        if cell_id == "mainframe":
            focus_retry_count += 1
            log(
                "click_code",
                "포커스 재시도",
                f"포커스가 mainframe에 있음 → 재시도 {focus_retry_count}/{focus_retry_limit}",
            )
            first_cell.click()
            send_arrow_down_native(driver)
            time.sleep(delay)
            if focus_retry_count >= focus_retry_limit:
                log("click_code", "치명오류", "초기 포커스 이동 실패 → 루프 강제 종료")
                return
            continue

        if "gdList.body.gridrow" not in cell_id or not cell_id.endswith("_0_0"):
            log("click_code", "경고", f"포커스 셀 ID 이상: {cell_id}")
            time.sleep(delay)
            continue

        code = focused.text.strip()
        log("click_code", "포커스 확인", f"포커스된 코드: {code} / 셀 ID: {cell_id}")
        log("click_code", "실행", f"코드 {code} 클릭")
        focused.click()
        code_counts[code] = code_counts.get(code, 0) + 1
        last_cell_id = cell_id

        if code == last_code:
            repeat_count += 1
        else:
            repeat_count = 1
            last_code = code

        if repeat_count >= repeat_limit:
            log("click_code", "종료", f"코드 {code} {repeat_limit}회 이상 반복 → 종료")
            break

        # \ubc29\ud5a5\ud0a4 \u2193 \uc785\ub825 \uc804 \ud604\uc7ac \uc140 ID \uc800\uc7a5
        prev_cell_id = cell_id

        # \u2193 \ud0a4 \uc785\ub825 (CDP native)
        send_arrow_down_native(driver)
        time.sleep(delay)

        # \u2193 \uc785\ub825 \ud6c4 \ud3ec\uce20\uc0ac\ub41c \uc140 ID \ub2e4\uc2dc \uc77d\uae30
        new_focused = driver.switch_to.active_element
        new_cell_id = new_focused.get_attribute("id") or ""

        log("click_code", "위치확인", f"CDP ↓ 입력 후 포커스된 셀 ID: {new_cell_id}")

        if new_cell_id == prev_cell_id:
            log(
                "click_code",
                "\uacbd\uace0",
                f"CDP ↓ 입력 후에도 셀 이동 없음 (셀 ID 동일: {new_cell_id})",
            )
        else:
            log(
                "click_code",
                "\uc774\ub3d9",
                f"CDP ↓ 입력으로 셀 이동 성공 → {prev_cell_id} → {new_cell_id}",
            )

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


def click_codes_by_loop(driver, row_limit: int = 50) -> None:
    """Sequentially click grid cells by ID without using Arrow keys.

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver instance.
    row_limit : int, optional
        Maximum number of grid rows to iterate over.
    """

    base_id = (
        "mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm"
        ".form.div2.form.gdList.body"
    )

    rows = driver.find_elements(By.XPATH, f"//*[contains(@id, '{base_id}.gridrow_')]")
    total_rows = min(len(rows), row_limit)

    log(
        "click_code",
        "행개수확인",
        f"로드 된 그리드 행 수: {len(rows)} → 순회 대상: {total_rows}",
    )

    for i in range(total_rows):
        cell_id = f"{base_id}.gridrow_{i}.cell_0_0"
        try:
            cell = driver.find_element(By.ID, cell_id)
            code = cell.text.strip()
            log("click_code", "셀확인", f"[{i}] ID: {cell_id}, 코드: '{code}' → 클릭")
            cell.click()
            time.sleep(0.3)
        except Exception as e:
            log("click_code", "오류", f"[{i}] 셀 접근 실패: {e}")


def scroll_loop_click(driver, start_index: int = 0, max_attempts: int = 100, scroll: bool = True) -> None:
    """Sequentially click grid cells until a cell is missing.

    Parameters
    ----------
    driver : WebDriver
        Selenium WebDriver instance.
    start_index : int, optional
        Index of the first grid row to click.
    max_attempts : int, optional
        Maximum iterations before aborting.
    scroll : bool, optional
        Whether to scroll the cell into view before clicking.
    """
    from selenium.common.exceptions import NoSuchElementException

    base_id = (
        "mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm"
        ".form.div2.form.gdList.body"
    )

    i = start_index
    attempts = 0
    while attempts < max_attempts:
        cell_id = f"{base_id}.gridrow_{i}.cell_0_0"
        try:
            cell = driver.find_element(By.ID, cell_id)
            if scroll:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", cell
                )
            cell.click()
            log("scroll_loop", "실행", f"[{i}] 클릭 성공")
            i += 1
            attempts += 1
            time.sleep(0.3)
        except NoSuchElementException:
            log("scroll_loop", "완료", f"[{i}] 셀 없음 → 종료")
            break


def grid_scroll_click_loop(
    driver,
    grid_id_prefix: str,
    cell_suffix: str,
    max_rows: int = 100,
    scroll_into_view: bool = True,
    log_enabled: bool = True,
) -> None:
    """Click grid cells sequentially with optional scrolling."""
    from selenium.common.exceptions import NoSuchElementException

    for i in range(max_rows):
        cell_id = f"{grid_id_prefix}{i}{cell_suffix}"
        try:
            cell = driver.find_element(By.ID, cell_id)
            if scroll_into_view:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", cell
                )
            cell.click()
            if log_enabled:
                log("grid_scroll", "실행", f"[{i}] 클릭 완료: {cell_id}")
            time.sleep(0.2)
        except NoSuchElementException:
            if log_enabled:
                log("grid_scroll", "완료", f"[{i}] 셀 존재 안 함: {cell_id} → 루프 종료")
            break
