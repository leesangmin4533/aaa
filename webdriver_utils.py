from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

try:
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    # from webdriver_manager.chrome import ChromeDriverManager # 이 줄은 제거
    from selenium import webdriver
except ImportError as exc:  # pragma: no cover - dependency missing
    logging.getLogger(__name__).warning(
        "Selenium or webdriver-manager not available: %s", exc
    )
    raise

from utils.log_util import get_logger

SCRIPT_DIR: Path = Path(__file__).resolve().parent

logger = get_logger(__name__, level=logging.DEBUG)


def create_driver() -> Any:
    """Create and return a Selenium WebDriver instance."""
    # service = Service(ChromeDriverManager().install()) # 이 줄은 제거
    # Cloud Run 환경에 맞게 chromedriver 경로를 직접 지정
    service = Service("/usr/local/bin/chromedriver") # /usr/bin/chromedriver는 Dockerfile에서 설치한 chromium-driver의 경로

    options = Options()
    options.add_argument("--headless")  # GUI 없이 백그라운드에서 실행
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox") # 추가
    options.add_argument("--disable-extensions") # 추가
    options.add_argument("--disable-gpu") # GPU 사용 비활성화 (Cloud Run에 GPU 없음)
    options.add_argument("--window-size=1920,1080") # 창 크기 설정 (headless 모드에서 중요)
    options.add_argument("--single-process") # 단일 프로세스 모드

    driver = webdriver.Chrome(service=service, options=options)
    driver.command_executor.set_timeout(300)  # 명령어 실행 타임아웃을 300초로 설정
    driver.set_page_load_timeout(300)  # 페이지 로드 타임아웃을 300초로 설정
    driver.set_script_timeout(300)   # 스크립트 실행 타임아웃을 300초로 설정
    return driver


def wait_for_page_elements(driver: Any, timeout: int = 120) -> bool:
    """Wait for key elements on the '중분류 매출 구성비' page to be present.
    Specifically waits for the gdList body to appear.
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(
                "return !!document.querySelector('[id*=\"gdList\"][id*=\"body\"]');"
            )
        )
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(
                "const g=document.querySelector('[id*=\"gdList\"][id*=\"body\"]');"
                "return g && g.textContent.trim().length>0;"
            )
        )
        return True
    except Exception as e:  # pragma: no cover - best effort logging
        logger.error(f"wait_for_mix_ratio_page failed: {e}")
        try:
            for entry in driver.get_log("browser"):
                logger.error(entry.get("message"))
        except Exception:
            pass
        return False


def wait_for_dataset_to_load(driver: Any, timeout: int = 120) -> bool:
    """Waits for the dsList dataset to be loaded and stable."""
    logger.info("Waiting for dsList dataset to load...")
    try:
        # 1. Wait for the main form object to be available
        js_check_form = """
        const app = nexacro.getApplication();
        if (!app || !app.mainframe || !app.mainframe.HFrameSet00 || !app.mainframe.HFrameSet00.VFrameSet00 || !app.mainframe.HFrameSet00.VFrameSet00.FrameSet) return false;
        const form = app.mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0;
        return !!(form && form.form);
        """
        WebDriverWait(driver, 30).until(lambda d: d.execute_script(js_check_form))

        # 2. Wait for the dataset row count to be greater than 0 and stable
        js_get_rows = """
        const form = nexacro.getApplication().mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form;
        if (!form || !form.div_workForm || !form.div_workForm.form || !form.div_workForm.form.dsList) return 0;
        return form.div_workForm.form.dsList.getRowCount();
        """
        last_row_count = -1
        stable_since = time.time()
        start_time = time.time()

        while time.time() - start_time < timeout:
            row_count = driver.execute_script(js_get_rows)

            if row_count > 0:
                if row_count == last_row_count:
                    if time.time() - stable_since > 2:  # Stable for 2 seconds
                        logger.info(
                            f"Dataset loaded and stable with {row_count} rows."
                        )
                        return True
                else:
                    last_row_count = row_count
                    stable_since = time.time()

            time.sleep(0.5)

        logger.error(
            f"Timeout waiting for dataset to load and stabilize. Final row count: {last_row_count}"
        )
        return False

    except Exception as e:  # pragma: no cover - best effort logging
        logger.error(f"An error occurred while waiting for the dataset: {e}")
        return False


def run_script(driver: Any, name: str) -> Any:
    script_path = Path(SCRIPT_DIR) / name
    if not script_path.exists():
        raise FileNotFoundError(f"JavaScript file not found: {script_path}")
    script_text = script_path.read_text(encoding="utf-8")
    return driver.execute_script(script_text)