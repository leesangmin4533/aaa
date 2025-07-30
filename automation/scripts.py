import os
import time
from typing import Any

from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

from .config import log


def run_script(driver, name: str, scripts_dir) -> Any:
    """Read a JavaScript file from ``scripts_dir`` and execute it."""
    script_full_path = os.path.join(scripts_dir, name)
    log.debug(
        f"Checking script existence: {script_full_path}",
        extra={"tag": "run_script"},
    )
    if not os.path.exists(script_full_path):
        msg = f"script file not found: {script_full_path}"
        log.error(msg, extra={"tag": "run_script"})
        raise FileNotFoundError(msg)
    with open(script_full_path, "r", encoding="utf-8") as f:
        js = f.read()
    return driver.execute_script(js)


def wait_for_data(driver, timeout: int = 10) -> Any | None:
    """Poll for ``window.__parsedData__`` until available or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        data = driver.execute_script("return window.__parsedData__ || null")
        if data is not None:
            return data
        time.sleep(0.5)
    return None


def wait_for_mix_ratio_page(driver, timeout: int = 120) -> bool:
    """중분류별 매출 구성비 화면이 나타나고 데이터가 로드될 때까지 대기한다."""
    log.info(
        "중분류별 매출 구성비 페이지 로딩 대기 시작",
        extra={"tag": "navigation"},
    )

    try:
        # navigation.js가 이미 페이지를 로드하고 필요한 프레임으로 전환했다고 가정
        # 따라서, 직접적으로 gdList 그리드 컨테이너와 데이터 로딩을 기다립니다.

        # 1. 그리드 컨테이너 대기
        grid_js = """
        return !!document.querySelector('[id*="gdList"][id*="body"]');
        """
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(grid_js)
        )
        log.debug("그리드 컨테이너 발견됨", extra={"tag": "navigation"})

        # 2. 데이터 로딩 대기
        data_js = """
        const grid = document.querySelector('[id*="gdList"][id*="body"]');
        return grid && grid.textContent.trim().length > 0;
        """
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(data_js)
        )
        log.debug("데이터 로드 완료", extra={"tag": "navigation"})

        return True

    except TimeoutException:
        log.error(
            f"페이지 로드 시간 초과 ({timeout}초)", extra={"tag": "navigation"}
        )
        return False
    except Exception as e:
        log.error(
            f"페이지 로드 중 오류 발생: {str(e)}",
            extra={"tag": "navigation"},
            exc_info=True,
        )
        return False


def collect_mid_category_data(driver, scripts_dir: str) -> Any:
    """Execute the mid-category data collection script and return the data."""
    log.info(
        "Executing mid-category data collection script...",
        extra={"tag": "collect"},
    )
    try:
        result = run_script(driver, "get_mid_category_data.js", scripts_dir)
        if result and result.get("error"):
            log.error(
                f"Mid-category collection script failed: {result['error']}",
                extra={"tag": "collect"},
            )
            return None

        log.info(
            f"Successfully collected {len(result.get('data', []))} mid-categories.",
            extra={"tag": "collect"},
        )
        return result.get("data")
    except Exception as e:
        log.error(
            f"An error occurred while running the collection script: {e}",
            extra={"tag": "collect"},
            exc_info=True,
        )
        return None
