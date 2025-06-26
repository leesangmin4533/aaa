import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


CONFIG_FILE = "nexacro_id_input_js.json"


def load_config():
    """Load automation configuration from ``CONFIG_FILE``."""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    cfg = load_config()
    url = cfg["steps"][0]["value"]
    id_xpath = cfg["id_xpath"]
    js_code = cfg["steps"][3]["code"]

    driver = webdriver.Chrome()
    driver.get(url)

    # Wait until the Nexacro inputs are available
    wait_cfg = cfg["steps"][1]
    if wait_cfg.get("action") == "wait_elements_count":
        WebDriverWait(driver, wait_cfg.get("timeout", 20)).until(
            lambda d: len(d.find_elements(By.CLASS_NAME, wait_cfg["value"])) >= wait_cfg["count"]
        )

    try:
        id_input = driver.find_element(By.XPATH, id_xpath)
        driver.execute_script(js_code, id_input)
        print("\u2705 ID 입력 완료 (JavaScript 방식)")
        time.sleep(cfg["steps"][-1].get("seconds", 2))
    except Exception as e:
        print(f"Failed to input ID: {e}")

    input("Login screen displayed. Press Enter to exit...")
    time.sleep(3)
    driver.quit()


if __name__ == '__main__':
    main()
