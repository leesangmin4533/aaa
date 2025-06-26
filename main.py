import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait

CONFIG_FILE = "nexacro_idpw_input_physical.json"

def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def run_step(driver, step, elements):
    action = step["action"]
    if action == "open_url":
        driver.get(step["value"])
    elif action == "wait_elements_count":
        WebDriverWait(driver, step.get("timeout", 20)).until(
            lambda d: len(d.find_elements(getattr(By, step["by"].upper()), step["value"])) >= step["count"]
        )
    elif action == "find_element":
        elem = driver.find_element(getattr(By, step["by"].upper()), step["value"])
        if "as" in step:
            elements[step["as"]] = elem
    elif action == "click":
        elem = elements[step["target"]]
        elem.click()
    elif action == "send_keys":
        elem = elements[step["target"]]
        key = step["keys"]
        if key == "ENTER":
            ActionChains(driver).move_to_element(elem).click().send_keys(Keys.ENTER).perform()
        else:
            elem.send_keys(key)
    elif action == "sleep":
        time.sleep(step["seconds"])
    elif action == "script":
        # 현재는 사용 안 함, 필요시 복원 가능
        pass
    else:
        print(f"⚠ 알 수 없는 action: {action}")

    if "log" in step:
        print(step["log"])

def main():
    cfg = load_config()
    steps = cfg["steps"]
    driver = webdriver.Chrome()
    elements = {}

    for step in steps:
        try:
            run_step(driver, step, elements)
        except Exception as e:
            print(f"❌ Step 실패: {step.get('action')} → {e}")
            break

    input("⏸ 로그인 화면 유지. Enter 키를 누르면 종료됩니다...")
    driver.quit()

if __name__ == '__main__':
    main()
