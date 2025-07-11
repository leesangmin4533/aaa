from selenium.webdriver.remote.webdriver import WebDriver
from pathlib import Path
import json
import os
import time

from utils.log_util import create_logger
from utils.popup_util import (
    close_nexacro_popups,
    close_focus_popup,
    ensure_focus_popup_closed,
)

log = create_logger("login_bgf")


def _read_env_file(env_path: Path) -> dict:
    env: dict[str, str] = {}
    try:
        with env_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip() or line.strip().startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.strip().split("=", 1)
                env[key] = value
    except Exception:
        pass
    return env


def load_credentials(path: str | None = None) -> dict:
    """Load login credentials from environment, ``.env`` file, or a JSON file.

    환경 변수 ``BGF_USER_ID`` 와 ``BGF_PASSWORD`` 가 존재하면 이를 우선 사용한다.
    다음으로 현재 디렉터리의 ``.env`` 파일을 찾아 값을 읽는다. ``path`` 인자가
    주어지면 해당 JSON 파일을 읽어 로그인 정보를 반환한다. 세 방법 모두 실패하면
    :class:`RuntimeError` 를 발생시킨다.
    """

    env_id = os.environ.get("BGF_USER_ID")
    env_pw = os.environ.get("BGF_PASSWORD")

    if not (env_id and env_pw):
        env_path = Path(".env")
        if env_path.is_file():
            env = _read_env_file(env_path)
            env_id = env_id or env.get("BGF_USER_ID")
            env_pw = env_pw or env.get("BGF_PASSWORD")

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
                ensure_focus_popup_closed(driver)
                close_nexacro_popups(driver)
            except Exception as e:
                log("login", "WARNING", f"Popup close failed: {e}")
            else:
                log("login", "INFO", "팝업 모듈 종료: 다음 단계 진입")
            return True
    log("login", "FAIL", "Login check timeout")
    return False
