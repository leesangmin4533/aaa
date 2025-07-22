from selenium.webdriver.remote.webdriver import WebDriver
from pathlib import Path
import json
import os
import sys
import time
from dotenv import load_dotenv

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ``login_bgf.py`` 파일을 스크립트로 실행할 때도 상위 디렉터리의 모듈을
# 찾을 수 있도록 ``sys.path`` 에 프로젝트 루트 경로를 추가한다.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.log_util import get_logger
try:
    from utils.popup_util import close_all_modals
except Exception:  # pragma: no cover - fallback for tests
    def close_all_modals(*_a, **_k):
        return 0

log = get_logger(__name__)


def load_credentials(path: str | None = None) -> dict:
    """Load login credentials from a JSON file or environment variables.

    If a path to a JSON file is provided, it loads credentials from that file.
    Otherwise, it loads credentials from environment variables, which can be
    populated from a .env file.
    """
    # Load .env from the current working directory if present
    load_dotenv(dotenv_path=Path(".env"))

    user_id = os.environ.get("BGF_USER_ID")
    password = os.environ.get("BGF_PASSWORD")

    if user_id and password:
        return {"id": user_id, "password": password}

    if path:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load credentials from {path}: {e}")

    raise RuntimeError(
        "Credentials not provided. Set BGF_USER_ID/BGF_PASSWORD in .env or specify a JSON file."
    )


def login_bgf(
    driver: WebDriver, credential_path: str | None = None, timeout: int = 30
) -> bool:
    """Perform login on BGF Retail store page.

    Returns True if login succeeded, False otherwise.
    """
    url = "https://store.bgfretail.com/websrc/deploy/index.html"
    driver.get(url)
    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return !!(nexacro.getApplication() && nexacro.getApplication().mainframe);")
        )
    except Exception as e:
        log.error(f"Nexacro application did not load: {e}", extra={'tag': 'login'})
        return False

    creds = load_credentials(credential_path)
    user_id = creds.get("id")
    password = creds.get("password")

    js = f"""
try {{
    var form = nexacro.getApplication().mainframe.HFrameSet00.LoginFrame.form.div_login.form;

    form.edt_id.set_value("{user_id}");
    form.edt_id.text = "{user_id}";
    form.edt_id.setFocus();

    form.edt_pw.set_value("{password}");
    form.edt_pw.text = "{password}";
    form.edt_pw.setFocus();

    // 지연 실행
    setTimeout(() => form.btn_login.click(), 300);
}} catch (e) {{
    console.error("login error", e);
}}
"""
    try:
        # Wait for the login form elements to be ready
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return !!(nexacro.getApplication() && nexacro.getApplication().mainframe && nexacro.getApplication().mainframe.HFrameSet00.LoginFrame.form.div_login.form);")
        )
        log.info("Login form elements are ready.", extra={'tag': 'login'})
        driver.execute_script(js)
        log.info("Login script executed", extra={'tag': 'login'})
        pw_value = driver.execute_script(
            """
try {
    return nexacro.getApplication().mainframe.HFrameSet00.LoginFrame.form.div_login.form.edt_pw.value;
} catch (e) {
    return 'error: ' + e.toString();
}
"""
        )
        log.debug(f"[검증] 비밀번호 필드 값: {pw_value}", extra={'tag': 'login'})
    except Exception as e:
        log.error(f"JavaScript execution failed: {e}", extra={'tag': 'login'})
        return False

    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return nexacro.getApplication().GV_CHANNELTYPE === 'HOME';")
        )
        log.info("Login succeeded", extra={'tag': 'login'})
        try:
            time.sleep(1) # Give time for popups to appear after login
            closed_count = close_all_modals(driver)
            log.info(f"Closed {closed_count} popups after login.", extra={'tag': 'login'})
        except Exception as e:
            log.warning(f"An error occurred during popup closing: {e}", extra={'tag': 'login'})
        return True
    except Exception:
        log.error("Login check timeout or failed", extra={'tag': 'login'})
        print("Error: Login check timeout or failed")
        return False
