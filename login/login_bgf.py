from utils.log_util import get_logger
from pathlib import Path
import json
import os
import sys
import time
from typing import Any, Dict
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

log = get_logger(__name__)


def load_credentials(credential_keys: Dict[str, str]) -> dict:
    """Load login credentials from environment variables using provided keys.

    It loads credentials from environment variables, which can be
    populated from a .env file. The `credential_keys` dictionary specifies
    which environment variables to use for the ID and password.
    """
    # .env 파일을 명시적으로 로드합니다.
    env_path = ROOT_DIR / ".env"
    if env_path.exists():
        log.debug(f"Loading .env file from: {env_path}", extra={"tag": "env"})
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        log.warning(f".env file not found at {env_path}", extra={"tag": "env"})


    id_env_var = credential_keys.get("id")
    pw_env_var = credential_keys.get("password")

    if not id_env_var or not pw_env_var:
        raise ValueError("`credential_keys` must contain 'id' and 'password' keys.")

    user_id = os.environ.get(id_env_var)
    password = os.environ.get(pw_env_var)

    log.debug(
        f"Loading credentials from env vars: ID_VAR='{id_env_var}', PW_VAR='{pw_env_var}'",
        extra={"tag": "env"},
    )

    if user_id and password:
        return {"id": user_id, "password": password}

    raise RuntimeError(
        f"Credentials not found in environment variables. "
        f"Please set {id_env_var} and {pw_env_var} in your .env file."
    )


def login_bgf(
    driver: WebDriver, credential_keys: Dict[str, str], timeout: int = 30
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

    creds = load_credentials(credential_keys)
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
            from utils.popup_util import close_popups_after_delegate
            close_popups_after_delegate(driver)
        except Exception:
            log.warning(
                "Failed to close popups after login", extra={"tag": "login"}
            )
        return True
    except Exception:
        log.error("Login check timeout or failed", extra={"tag": "login"})
        print("Error: Login check timeout or failed")
        return False
