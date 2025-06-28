import json
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from dotenv import load_dotenv
import os

MODULE_NAME = "login"


def log(step: str, msg: str) -> None:
    print(f"\u25b6 [{MODULE_NAME} > {step}] {msg}")


def load_config(config_file):
    with open(config_file, "r", encoding="utf-8") as f:
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
            if isinstance(keys, str):
                keys = env.get(keys.strip("${}"), keys)
            ActionChains(driver).move_to_element(elem).click().send_keys(keys).perform()
    elif action == "script":
        code = step["code"]
        driver.execute_script(code, elements[step["target"]])
    elif action == "sleep":
        time.sleep(step["seconds"])
    elif action == "extract_texts":
        src = step["from"]
        prefix = src["xpath_prefix"]
        suffix = src["xpath_suffix"]
        row_count = step.get("rows", 0)
        results = []
        if isinstance(row_count, str) and row_count == "auto":
            i = 0
            while True:
                path = f"{prefix}{i}{suffix}"
                log("extract_xpath", f"시도 중인 XPath: {path}")
                try:
                    elem = driver.find_element(By.XPATH, path)
                    log("extract_found", f"텍스트 발견: {elem.text.strip()}")
                    results.append(elem.text.strip())
                    i += 1
                except Exception as e:
                    log("extract_missing", f"텍스트 없음 @ {path} → {e}")
                    break
        else:
            for i in range(row_count):
                path = f"{prefix}{i}{suffix}"
                log("extract_xpath", f"시도 중인 XPath: {path}")
                try:
                    elem = driver.find_element(By.XPATH, path)
                    log("extract_found", f"텍스트 발견: {elem.text.strip()}")
                    results.append(elem.text.strip())
                except Exception as e:
                    log("extract_missing", f"텍스트 없음 @ {path} → {e}")
                    break
        outfile = step.get("save_to")
        if outfile:
            os.makedirs(os.path.dirname(outfile), exist_ok=True)
            with open(outfile, "w", encoding="utf-8") as f:
                f.write("\n".join(results))
    elif action == "log":
        log("message", step["message"])
    else:
        log("unknown", f"알 수 없는 action: {action}")

    if "log" in step:
        log("step_log", step["log"])


def run_login(driver, config_path="login_sequence.json"):
    cfg = load_config(config_path)
    env = load_env()
    steps = cfg["steps"]
    elements = {}

    for step in steps:
        try:
            run_step(driver, step, elements, env)
        except Exception as e:
            log("step_fail", f"Step 실패: {step.get('action')} → {e}")
            break
