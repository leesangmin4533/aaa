from selenium.webdriver.remote.webdriver import WebDriver
from pathlib import Path
import json
import time

from utils.log_util import create_logger

log = create_logger("login_bgf")


def load_credentials(path: str | None = None) -> dict:
    """Load login credentials from a JSON file."""
    if path is None:
        path = Path(__file__).resolve().parent.parent / "credentials.json"
    else:
        path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load credentials: {e}")


def login_bgf(driver: WebDriver, credential_path: str | None = None, timeout: int = 10) -> bool:
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
    form.edt_id.killFocus();

    form.edt_pw.setFocus();
    form.edt_pw.set_value("{password}");
    form.edt_pw.killFocus();

    form.btn_login.click();
}} catch (e) {{
    console.error("login error", e);
}}
"""
    try:
        driver.execute_script(js)
        log("login", "INFO", "Login script executed")
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
            return True
    log("login", "FAIL", "Login check timeout")
    return False
