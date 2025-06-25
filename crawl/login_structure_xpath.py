import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By

URL = "https://store.bgfretail.com/websrc/deploy/index.html"

XPATHS = {
    "id_xpath": "//input[@id='mainframe.HFrameSet00.LoginFrame.form.div_login.form.edt_id:input']",
    "password_xpath": "//input[@id='mainframe.HFrameSet00.LoginFrame.form.div_login.form.edt_pw:input']",
    "submit_xpath": "//div[@id='mainframe.HFrameSet00.LoginFrame.form.div_login.form.btn_login:iconElement']",
}


def create_login_structure_xpath(fail_on_missing: bool = True) -> None:
    """Create ``login_structure_xpath.json`` by validating known XPaths."""
    os.makedirs("structure", exist_ok=True)

    driver = None
    try:
        driver = webdriver.Chrome()
        driver.get(URL)

        # Ensure elements exist on the page. If any lookup fails an exception is
        # raised so the caller can abort the workflow early.
        driver.find_element(By.XPATH, XPATHS["id_xpath"])
        driver.find_element(By.XPATH, XPATHS["password_xpath"])
        driver.find_element(By.XPATH, XPATHS["submit_xpath"])
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
