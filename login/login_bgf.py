from selenium.webdriver.remote.webdriver import WebDriver
from pathlib import Path
import json
import os
import time

from utils.log_util import create_logger
from utils.popup_util import close_nexacro_popups, close_focus_popup

log = create_logger("login_bgf")


def load_credentials(path: str | None = None) -> dict:
    """Load login credentials from environment or a JSON file.

    환경 변수 ``BGF_USER_ID`` 와 ``BGF_PASSWORD`` 가 존재하면 이를 우선 사용한다.
    ``path`` 인자가 주어지면 해당 JSON 파일을 읽어 로그인 정보를 반환한다.
    둘 다 제공되지 않으면 :class:`RuntimeError` 를 발생시킨다.
    """

    env_id = os.environ.get("BGF_USER_ID")
    env_pw = os.environ.get("BGF_PASSWORD")
    if env_id and env_pw:
        return {"id": env_id, "password": env_pw}

    if path is None:
        raise RuntimeError(
            "Credentials not provided. Set BGF_USER_ID/BGF_PASSWORD or specify a file"
        )

    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load credentials from {path}: {e}")


def login_bgf(
    driver: WebDriver, credential_path: str | None = None, timeout: int = 10
) -> bool:
    """Perform login on BGF Retail store page.

    Returns True if login succeeded, False otherwise.
    """
    url = "https://store.bgfretail.com/websrc/deploy/index.html"
    driver.get(url)
    time.sleep(3)  # Wait for Nexacro app to load

    creds = load_credentials(credential_path)
    user_id = creds.get("id")
    password = creds.get("password")

    js = f"""
try {{
    var form = nexacro.getApplication().mainframe.HFrameSet00.LoginFrame.form.div_login.form;

    form.edt_id.setFocus();
    form.edt_id.set_value("{user_id}");
    form.edt_id.text = "{user_id}";

    form.edt_pw.setFocus();
    form.edt_pw.set_value("{password}");
    form.edt_pw.text = "{password}";

    // 포커스 이동으로 이벤트 유도
    form.edt_id.setFocus();

    // 지연 실행
    setTimeout(() => form.btn_login.click(), 500);
}} catch (e) {{
    console.error("login error", e);
}}
"""
    try:
        driver.execute_script(js)
        log("login", "INFO", "Login script executed")
        pw_value = driver.execute_script(
            """
try {
    return nexacro.getApplication().mainframe.HFrameSet00.LoginFrame.form.div_login.form.edt_pw.value;
} catch (e) {
    return 'error: ' + e.toString();
}
"""
        )
        log("login", "DEBUG", f"[검증] 비밀번호 필드 값: {pw_value}")
    except Exception as e:
        log("login", "ERROR", f"JavaScript execution failed: {e}")
        return False

    for _ in range(timeout):
        time.sleep(1)
        try:
            success = driver.execute_script(
                "return nexacro.getApplication().GV_CHANNELTYPE === 'HOME';"
            )
        except Exception:
            success = False
        if success:
            log("login", "SUCCESS", "Login succeeded")
            try:
                close_focus_popup(driver)
                close_nexacro_popups(driver)
            except Exception as e:
                log("login", "WARNING", f"Popup close failed: {e}")
            return True
    log("login", "FAIL", "Login check timeout")
    return False
