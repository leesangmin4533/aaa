import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from dotenv import load_dotenv

URL = "https://store.bgfretail.com/websrc/deploy/index.html"

XPATHS = {
    "id_xpath": "//input[@id='mainframe.HFrameSet00.LoginFrame.form.div_login.form.edt_id:input']",
    "password_xpath": "//input[@id='mainframe.HFrameSet00.LoginFrame.form.div_login.form.edt_pw:input']",
    "submit_xpath": "//div[@id='mainframe.HFrameSet00.LoginFrame.form.div_login.form.btn_login:iconElement']",
}


def create_login_structure_xpath(fail_on_missing: bool = True) -> None:
    """Create ``login_structure_xpath.json`` by validating known XPaths."""
    os.makedirs("structure", exist_ok=True)

    load_dotenv()
    login_id = os.getenv("LOGIN_ID")
    login_pw = os.getenv("LOGIN_PW")

    driver = None
    try:
        driver = webdriver.Chrome()
        driver.get(URL)

        # Wait until the Nexacro-based login form is fully rendered. The SPA
        # may load elements dynamically so the usual presence check is not
        # sufficient on some slow environments. Execute a small JavaScript
        # snippet that evaluates when the targeted element becomes available
        # in the DOM and only then continue to locate it by XPath.
        WebDriverWait(driver, 20).until(
            lambda d: len(d.find_elements(By.CLASS_NAME, "nexainput")) >= 2
        )
        inputs = driver.find_elements(By.CLASS_NAME, "nexainput")
        driver.execute_script(
            "arguments[0].value = arguments[1];",
            inputs[0],
            login_id,
        )
        driver.execute_script(
            "arguments[0].value = arguments[1];",
            inputs[1],
            login_pw,
        )
        login_btn = driver.find_element(By.XPATH, "//div[@id='mainframe.HFrameSet00.LoginFrame.form.div_login.form.btn_login:icontext']")
        login_btn.click()
    except Exception as exc:
        if fail_on_missing:
            raise RuntimeError("Required login element not found") from exc
    finally:
        if driver:
            driver.quit()

    cfg = {"url": URL, **XPATHS}
    with open(os.path.join("structure", "login_structure_xpath.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    create_login_structure_xpath()
