"""
중분류별 매출 데이터 수집 자동화 스크립트

데이터 저장 정책:
1. DB 우선: DB가 기준이며, 텍스트 파일은 보조 용도
2. 저장 범위: 텍스트의 모든 항목을 DB에 저장
3. 시각 기록: collected_at은 분 단위까지 기록 (YYYY-MM-DD HH:MM)
4. 실행 기준: 프로그램 실행 시각 기준으로 기록
5. 중복 방지: 같은 날 동일 product_code의 sales가 증가하지 않으면 저장 제외
6. DB 관리: 날짜별 독립 DB 파일 생성 (예: 20250718.db)
"""

from __future__ import annotations

# Standard library imports
import os
import time
from pathlib import Path
from typing import Any
from datetime import datetime

# Third-party imports - Selenium 관련
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

# Local imports - 프로젝트 내부 모듈
from login.login_bgf import login_bgf
from utils.popup_util import close_popups_after_delegate
from utils.log_parser import extract_tab_lines
from utils import append_unique_lines, convert_txt_to_excel
from utils.db_util import write_sales_data
from utils.log_util import create_logger

# Directory configuration
SCRIPT_DIR = Path(__file__).with_name("scripts")
CODE_OUTPUT_DIR = Path(__file__).with_name("code_outputs")

# Script file configuration
DEFAULT_SCRIPT = "auto_collect_mid_products.js"  # 자동 데이터 수집 스크립트
LISTENER_SCRIPT = "data_collect_listener.js"     # 데이터 수집 이벤트 리스너
NAVIGATION_SCRIPT = "navigation.js"              # 페이지 네비게이션 스크립트

# Logger used for both console and file output
log = create_logger("main")


def get_script_files() -> list[str]:
    """Return all JavaScript file names in the scripts directory sorted by name."""
    return sorted(p.name for p in SCRIPT_DIR.glob("*.js"))

# code_outputs/날짜.txt 필드 저장 순서를 지정한다.
FIELD_ORDER = [
    "midCode",
    "midName",
    "productCode",
    "productName",
    "sales",
    "order",
    "purchase",
    "discard",
    "stock",
]


def create_driver() -> webdriver.Chrome:
    options = Options()
    options.add_experimental_option("detach", True)
    caps = DesiredCapabilities.CHROME.copy()
    caps["goog:loggingPrefs"] = {"browser": "ALL"}
    for key, value in caps.items():
        options.set_capability(key, value)
    return webdriver.Chrome(service=Service(), options=options)


def run_script(driver: webdriver.Chrome, name: str) -> Any:
    path = SCRIPT_DIR / name
    if not path.exists():
        msg = f"script file not found: {path}"
        print(msg)
        log("run_script", "ERROR", msg)
        raise FileNotFoundError(msg)
    with open(path, "r", encoding="utf-8") as f:
        js = f.read()
    return driver.execute_script(js)


def wait_for_data(driver: webdriver.Chrome, timeout: int = 10):
    for _ in range(timeout * 2):
        try:
            data = driver.execute_script("return window.__parsedData__ || null")
            if data:
                return data
        except Exception:
            pass
        time.sleep(0.5)
    return None


def wait_for_mix_ratio_page(driver: webdriver.Chrome, timeout: int = 10) -> bool:
    """중분류별 매출 구성비 화면의 그리드가 나타날 때까지 대기한다."""
    js = (
        "return document.querySelector("
        "\"div[id*='gdList.body'][id*='cell_'][id$='_0:text']\""
        ") !== null;"
    )
    for _ in range(timeout * 2):
        try:
            if driver.execute_script(js):
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def save_to_txt(data: Any, output: str | Path | None = None) -> Path:
    """
    수집된 데이터를 텍스트 파일로 저장합니다.
    
    데이터 저장 규칙:
    1. 기본 파일명: YYYYMMDD.txt (예: 20250718.txt)
    2. 필드 구분자: 탭(\t)
    3. 필드 순서: FIELD_ORDER에 정의된 순서대로 저장
    4. 빈 값 처리: sales 관련 필드의 빈 값은 "0"으로 처리
    
    Parameters
    ----------
    data : Any
        저장할 데이터 (리스트 또는 딕셔너리)
    output : str | Path | None
        저장할 파일 경로 (없으면 자동 생성)
        
    Returns
    -------
    Path
        저장된 파일의 경로
    """
    # 파일 경로 설정
    if output is None:
        CODE_OUTPUT_DIR.mkdir(exist_ok=True)
        fname = datetime.now().strftime("%Y%m%d") + ".txt"
        output = CODE_OUTPUT_DIR / fname
        
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    # 기존 파일이 있으면 삭제
    if output.exists():
        output.unlink()
        
    # 데이터 저장
    with open(output, "w", encoding="utf-8") as f:
        if isinstance(data, list):
            for row in data:
                if isinstance(row, dict):
                    # 정의된 필드 순서대로 데이터 저장
                    f.write(
                        "\t".join(str(row.get(k, "")) for k in FIELD_ORDER) + "\n"
                    )
                else:
                    # 텍스트 데이터 처리 (빈 값은 0으로 변환)
                    text = str(row).rstrip("\n")
                    parts = text.split("\t")
                    if len(parts) >= 3:
                        for i in range(3, len(parts)):
                            if parts[i] == "":
                                parts[i] = "0"
                        text = "\t".join(parts)
                    f.write(text + "\n")
        else:
            # 단일 데이터 저장
            f.write(str(data))
    return output


def main() -> None:
    """
    메인 실행 함수: 브라우저를 실행하고 데이터를 수집하여 저장합니다.
    """
    # 브라우저 드라이버 초기화 및 로그인
    driver = create_driver()
    cred_path = os.environ.get("CREDENTIAL_FILE")
    if not login_bgf(driver, credential_path=cred_path):
        print("로그인 실패")
        log("login", "ERROR", "로그인 실패")
        driver.quit()
        return

    # 팝업 처리 및 페이지 네비게이션
    try:
        close_popups_after_delegate(driver)  # TensorFlow delegate 초기화 후 팝업 처리
    except Exception as e:
        print(f"팝업 처리 실패: {e}")
        log("popup", "WARNING", f"팝업 처리 실패: {e}")

    # 매출분석 화면으로 이동
    run_script(driver, NAVIGATION_SCRIPT)
    if not wait_for_mix_ratio_page(driver):
        print("페이지 로드 시간 초과")
        log("navigation", "ERROR", "페이지 로드 시간 초과")
        driver.quit()
        return



    # 중분류 매출 구성비 화면 진입 후 자동 수집 스크립트를 실행한다
    date_str = datetime.now().strftime("%y%m%d")
    output_path = CODE_OUTPUT_DIR / f"{date_str}.txt"
    if output_path.exists():
        output_path.unlink()

    run_script(driver, DEFAULT_SCRIPT)
    run_script(driver, LISTENER_SCRIPT)

    logs = driver.execute_script("return window.__midCategoryLogs__ || []")
    if logs:
        print("중분류 클릭 로그:", logs)
        log("mid_category", "INFO", f"logs: {logs}")

    while True:
        lines = driver.execute_script(
            "var d = window.__liveData__ || []; window.__liveData__ = []; return d;"
        )
        if lines:
            added = append_unique_lines(output_path, lines)
            print(f"appended {added} lines")
            log("collect", "INFO", f"appended {added} lines")

        parsed = driver.execute_script("return window.__parsedData__ || null")
        if parsed is not None:
            break
        time.sleep(0.5)

    db_path = CODE_OUTPUT_DIR / f"{datetime.now():%Y%m%d}.db"
    try:
        inserted = write_sales_data(parsed, db_path)
        print(f"db saved to {db_path}, inserted {inserted} rows")
        log("db", "INFO", f"db saved to {db_path}, inserted {inserted} rows")
    except Exception as e:
        print(f"db write failed: {e}")
        log("db", "ERROR", f"db write failed: {e}")

    print(f"saved to {output_path}")
    log("output", "INFO", f"saved to {output_path}")
    time.sleep(3)
    excel_dir = CODE_OUTPUT_DIR / "mid_excel"
    excel_dir.mkdir(parents=True, exist_ok=True)
    excel_path = excel_dir / f"{date_str}.xlsx"

    try:
        convert_txt_to_excel(str(output_path), str(excel_path))
        print(f"converted to {excel_path}")
        log("excel", "INFO", f"converted to {excel_path}")
    except Exception as e:
        print(f"excel conversion failed: {e}")
        log("excel", "ERROR", f"excel conversion failed: {e}")

    error = None
    # 스크립트 오류 확인
    try:
        error = driver.execute_script("return window.__parsedDataError__ || null")
        if error:
            print("스크립트 오류:", error)
            log("script", "ERROR", f"스크립트 오류: {error}")
    except Exception:
        pass

    # 브라우저 로그 수집 및 분석
    try:
        logs = driver.get_log("browser")
        if logs:
            # 탭으로 구분된 데이터 라인 추출
            lines = extract_tab_lines(logs)
            if lines:
                print("추출된 로그 데이터:")
                log("browser_log", "INFO", "추출된 로그 데이터:")
                for line in lines:
                    print(line)
                    log("browser_log", "INFO", line)
            else:
                # 일반 브라우저 콘솔 로그 출력
                print("브라우저 콘솔 로그:")
                log("browser_log", "INFO", "브라우저 콘솔 로그:")
                for entry in logs:
                    print(entry)
                    log("browser_log", "INFO", str(entry))
    except Exception as e:
        print(f"브라우저 로그 수집 실패: {e}")
        log("browser_log", "ERROR", f"브라우저 로그 수집 실패: {e}")


if __name__ == "__main__":
    main()
