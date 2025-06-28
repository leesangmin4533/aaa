import json
from modules.common.login import run_step, load_env
from modules.common.driver import create_chrome_driver


def run_script(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        steps = json.load(f)["steps"]
    env = load_env()

    driver = create_chrome_driver()
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
