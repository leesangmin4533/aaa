import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By

URL = "https://store.bgfretail.com/websrc/deploy/index.html"


def create_login_structure(fail_on_missing: bool = True) -> None:
    """Create ``login_structure.json`` by inspecting the live login page.

    If ``fail_on_missing`` is ``True`` and any required element cannot be
    located, a ``RuntimeError`` is raised so the caller can abort the
    workflow.
    """
    os.makedirs("structure", exist_ok=True)

    driver = None
    try:
        driver = webdriver.Chrome()
        driver.get(URL)

        id_elem = driver.find_element(By.ID, "input_id")
        id_attr = id_elem.get_attribute("id") or "input_id"
        id_selector = f"#{id_attr}"

        pw_elem = driver.find_element(By.ID, "input_pw")
        pw_attr = pw_elem.get_attribute("id") or "input_pw"
        password_selector = f"#{pw_attr}"

        driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_selector = "button[type='submit']"
    except Exception as exc:
        if fail_on_missing:
            raise RuntimeError("Required login element not found") from exc
    finally:
        if driver:
            driver.quit()

    cfg = {
        "url": URL,
        "id_selector": id_selector,
        "password_selector": password_selector,
        "submit_selector": submit_selector,
    }
    with open(os.path.join("structure", "login_structure.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    create_login_structure()
