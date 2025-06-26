import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from dotenv import load_dotenv
import os

CONFIG_FILE = "nexacro_idpw_input_js.json"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_env():
    load_dotenv()
    return {
        "LOGIN_ID": os.getenv("LOGIN_ID"),
        "LOGIN_PW": os.getenv("LOGIN_PW"),
    }


def run_step(driver, step, elements, env):
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
        elements[step["target"]].click()

    elif action == "send_keys":
        elem = elements[step["target"]]
        keys = step["keys"]

        # \u2705 \ubcc0\uc218 \ud070\uc791 \ucc98\ub9ac
        if isinstance(keys, str):
            keys = env.get(keys.strip("${}"), keys)

        if isinstance(keys, list):
            for item in keys:
                k = item["key"]
                if k == "ENTER":
                    ActionChains(driver).move_to_element(elem).click().send_keys(Keys.ENTER).perform()
                else:
                    ActionChains(driver).move_to_element(elem).click().send_keys(k).perform()
                if "delay" in item:
                    time.sleep(item["delay"])
        else:
            elem.send_keys(keys)

    elif action == "script":
        code = step["code"]
        driver.execute_script(code, elements[step["target"]])

    elif action == "sleep":
        time.sleep(step["seconds"])

    elif action == "log":
        print(step["message"])

    else:
        print(f"⚠ 알 수 없는 action: {action}")

    if "log" in step:
        print(step["log"])


def main():
    cfg = load_config()
    env = load_env()
    steps = cfg["steps"]
    driver = webdriver.Chrome()
    elements = {}

    for step in steps:
        try:
            run_step(driver, step, elements, env)
        except Exception as e:
            print(f"❌ Step 실패: {step.get('action')} → {e}")
            break

    input("⏸ 로그인 화면 유지 중. Enter를 누르면 종료됩니다.")
    driver.quit()


if __name__ == "__main__":
    main()
