import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By

URL = "https://store.bgfretail.com/websrc/deploy/index.html"


def create_login_structure() -> None:
    """Create ``login_structure.json`` by inspecting the live login page."""
    os.makedirs("structure", exist_ok=True)

    id_selector = "input[type='text']"
    password_selector = "input[type='password']"
    submit_selector = "button[type='submit']"

    driver = None
    try:
        driver = webdriver.Chrome()
        driver.get(URL)

        try:
            elem = driver.find_element(By.ID, "input_id")
            elem_id = elem.get_attribute("id")
            if elem_id:
                id_selector = f"#{elem_id}"
        except Exception:
            pass

        try:
            elem = driver.find_element(By.ID, "input_pw")
            elem_id = elem.get_attribute("id")
            if elem_id:
                password_selector = f"#{elem_id}"
        except Exception:
            pass

        try:
            driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_selector = "button[type='submit']"
        except Exception:
            pass
    except Exception:
        # Fallback to generic selectors when the browser cannot access the page
        pass
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
