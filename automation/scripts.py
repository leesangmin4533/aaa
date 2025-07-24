import os
import time
from typing import Any

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .config import log


def run_script(driver, name: str, scripts_dir) -> Any:
    """Read a JavaScript file from ``scripts_dir`` and execute it."""
    script_full_path = os.path.join(scripts_dir, name)
    log.debug(f"Checking script existence: {script_full_path}", extra={"tag": "run_script"})
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
    log.info("중분류별 매출 구성비 페이지 로딩 대기 시작", extra={"tag": "navigation"})
    
    try:
        # 1. mainframe 로딩 대기 (이미 전환되어 있을 수 있으므로 존재 여부만 확인)
        log.info("mainframe 로딩 상태 확인 시작", extra={"tag": "navigation"})
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[name="mainframe"]'))
        )
        # 이미 navigation.js에서 전환되었을 수 있으므로, 다시 전환 시도 (안전하게)
        try:
            driver.switch_to.default_content() # 메인 프레임으로 돌아간 후
            mainframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[name="mainframe"]'))
            )
            driver.switch_to.frame(mainframe)
            log.debug("mainframe으로 전환 완료", extra={"tag": "navigation"})
        except Exception as e:
            log.warning(f"mainframe 재전환 실패 또는 이미 전환됨: {e}", extra={"tag": "navigation"})
            # 이미 전환되어 있는 경우를 위해 현재 프레임 유지

        # 2. 그리드 컨테이너 대기
        grid_js = """
        return !!document.querySelector('[id*="gdList"][id*="body"]');
        """
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(grid_js)
        )
        log.debug("그리드 컨테이너 발견됨", extra={"tag": "navigation"})
        
        # 3. 데이터 로딩 대기
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
        log.error(f"페이지 로드 시간 초과 ({timeout}초)", extra={"tag": "navigation"})
        return False
    except Exception as e:
        log.error(f"페이지 로드 중 오류 발생: {str(e)}", extra={"tag": "navigation"}, exc_info=True)
        return False
