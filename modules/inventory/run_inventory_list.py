import json
from selenium import webdriver
from login_runner import run_step, load_env


def run_script(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        steps = json.load(f)["steps"]
    env = load_env()
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

    options = webdriver.ChromeOptions()
    options.add_argument("--remote-debugging-port=9222")
    caps = DesiredCapabilities.CHROME.copy()
    caps["goog:loggingPrefs"] = {"performance": "ALL"}
    driver = webdriver.Chrome(options=options, desired_capabilities=caps)
    elements = {}
    for step in steps:
        try:
            run_step(driver, step, elements, env)
        except Exception as e:
            print(f"❌ Step failed: {step.get('action')} → {e}")
            break
    input("⏸ Automation complete. Press Enter to exit.")
    driver.quit()


if __name__ == "__main__":
    run_script("modules/inventory/inventory_list_cmd.json")
