from utils.log_util import get_logger
from pathlib import Path
import json
import os
import sys
import time
from typing import Any
from dotenv import load_dotenv

try:  # pragma: no cover - optional selenium dependency
    from selenium.webdriver.remote.webdriver import WebDriver
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
except Exception:  # pragma: no cover - allow import failure in tests
    WebDriver = Any  # type: ignore

    def _dummy_wait(*_a, **_k):
        return None

    WebDriverWait = _dummy_wait  # type: ignore
    EC = None  # type: ignore

# ``login_bgf.py`` 파일을 스크립트로 실행할 때도 상위 디렉터리의 모듈을
# 찾을 수 있도록 ``sys.path`` 에 프로젝트 루트 경로를 추가한다.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from utils.popup_util import close_popups_after_delegate
except Exception:  # pragma: no cover - fallback for tests

    def close_popups_after_delegate(*_a, **_k):
        return 0


log = get_logger(__name__)


def load_credentials(path: str | None = None) -> dict:
    """Load login credentials from a JSON file or environment variables.

    If a path to a JSON file is provided, it loads credentials from that file.
    Otherwise, it loads credentials from environment variables, which can be
    populated from a .env file.
    """
    # 현재 작업 디렉터리의 ``.env`` 파일을 먼저 시도한다
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        log.debug(
            f"Attempting to load .env from CWD: {cwd_env}",
            extra={"tag": "env"},
        )
        load_dotenv(dotenv_path=cwd_env, override=False)

    log.debug(
        f"BGF_USER_ID after load_dotenv: {os.environ.get('BGF_USER_ID')}",
        extra={"tag": "env"},
    )
    log.debug(
        f"BGF_PASSWORD after load_dotenv: {os.environ.get('BGF_PASSWORD')}",
        extra={"tag": "env"},
    )

    if path:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load credentials from {path}: {e}")

    # 환경 변수에서 자격 증명 로드
    user_id = os.environ.get("BGF_USER_ID")
    password = os.environ.get("BGF_PASSWORD")

    if user_id and password:
        return {"id": user_id, "password": password}

    raise RuntimeError(
        "Credentials not provided. Set BGF_USER_ID/BGF_PASSWORD in .env or "
        "specify a JSON file."
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
        ready_check_js = (
            "return typeof nexacro !== 'undefined' && !!("
            "nexacro.getApplication()"
            " && nexacro.getApplication().mainframe)"
        )
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(ready_check_js)
        )
    except Exception as e:
        log.error(
            f"Nexacro application did not load: {e}", extra={"tag": "login"}
        )
        return False

    creds = load_credentials(credential_path)
    user_id = creds.get("id")
    password = creds.get("password")

    js = f"""
try {{
    var app = nexacro.getApplication();
    if (!app) return 'nexacro application not found';
    var mainframe = app.mainframe;
    if (!mainframe) return 'mainframe not found';
    var hFrameSet00 = mainframe.HFrameSet00;
    if (!hFrameSet00) return 'HFrameSet00 not found';
    var loginFrame = hFrameSet00.LoginFrame;
    if (!loginFrame) return 'LoginFrame not found';
    var form = loginFrame.form.div_login.form;
    if (!form) return 'login form not found';

    // Wait for input fields to be available
    var idInput = form.edt_id;
    var pwInput = form.edt_pw;
    if (!idInput || !pwInput) return 'Login input fields not found';

    idInput.set_value("{user_id}");
    idInput.text = "{user_id}";
    idInput.setFocus();

    pwInput.set_value("{password}");
    pwInput.text = "{password}";
    pwInput.setFocus();

    // 지연 실행
    setTimeout(() => form.btn_login.click(), 300);
}} catch (e) {{
    console.error("login error", e);
    return 'JavaScript error: ' + e.message;
}}
"""
    try:
        # Wait for the login form elements to be ready
        # This check is now more robust within the JS itself
        form_check_js = (
            "return typeof nexacro !== 'undefined' && !!("
            "nexacro.getApplication()"
            " && nexacro.getApplication().mainframe"
            " && nexacro.getApplication().mainframe.HFrameSet00"
            " && nexacro.getApplication().mainframe.HFrameSet00.LoginFrame"
            " && nexacro.getApplication().mainframe.HFrameSet00.LoginFrame."
            "form"
            " && nexacro.getApplication().mainframe.HFrameSet00.LoginFrame."
            "form.div_login"
            " && nexacro.getApplication().mainframe.HFrameSet00.LoginFrame."
            "form.div_login.form"
            ")"
        )
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(form_check_js)
        )
        log.info("Login form elements are ready.", extra={"tag": "login"})
        js_result = driver.execute_script(js)
        if isinstance(js_result, str) and js_result.startswith(
            "JavaScript error"
        ):
            raise RuntimeError(js_result)
        log.info("Login script executed", extra={"tag": "login"})
        pw_value = driver.execute_script(
            """
try {
    var app = nexacro.getApplication();
    if (!app) return 'nexacro application not found';
    var mainframe = app.mainframe;
    if (!mainframe) return 'mainframe not found';
    var hFrameSet00 = mainframe.HFrameSet00;
    if (!hFrameSet00) return 'HFrameSet00 not found';
    var loginFrame = hFrameSet00.LoginFrame;
    if (!loginFrame) return 'LoginFrame not found';
    var form = loginFrame.form.div_login.form;
    if (!form) return 'login form not found';
    return form.edt_pw.value;
} catch (e) {
    return 'error: ' + e.toString();
}
"""
        )
        log.debug(
            f"[검증] 비밀번호 필드 값: {pw_value}", extra={"tag": "login"}
        )
    except Exception as e:
        log.error(f"JavaScript execution failed: {e}", extra={"tag": "login"})
        return False

    try:
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(
                "return nexacro.getApplication().GV_CHANNELTYPE === 'HOME';"
            )
        )
        log.info("Login succeeded", extra={"tag": "login"})
        try:
            # Inject and start the popup monitor script.
            monitor_script_path = ROOT_DIR / "scripts" / "popup_monitor.js"
            if monitor_script_path.exists():
                monitor_script = monitor_script_path.read_text(encoding="utf-8")
                driver.execute_script(monitor_script)
                driver.execute_script("window.popupTools.startMonitor();")
                log.info("Popup monitor script injected and started.", extra={"tag": "login"})
            else:
                log.warning("Popup monitor script not found.", extra={"tag": "login"})
        except Exception as e:
            log.warning(
                f"An error occurred during popup monitoring setup: {e}",
                extra={"tag": "login"},
            )
        except Exception as e:
            log.warning(
                f"An error occurred during popup closing: {e}",
                extra={"tag": "login"},
            )
        return True
    except Exception:
        log.error("Login check timeout or failed", extra={"tag": "login"})
        print("Error: Login check timeout or failed")
        return False
