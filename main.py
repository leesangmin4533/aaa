import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys


CONFIG_FILE = "nexacro_idpw_input_physical.json"


def load_config():
    """Load automation configuration from ``CONFIG_FILE``."""
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)



def click_login_button(driver, cfg):
    """Force-click the login button using JavaScript."""
    login_btn_step = next(
        (step for step in cfg["steps"] if step.get("as") == "login_btn"),
        None,
    )
    if not login_btn_step:
        raise ValueError("login_btn step not found")
    login_btn_xpath = login_btn_step["value"]
    login_btn = driver.find_element(By.XPATH, login_btn_xpath)

    script_step = next(
        (
            step
            for step in cfg["steps"]
            if step.get("target") == "login_btn" and step.get("action") == "script"
        ),
        None,
    )
    script_code = (
        script_step.get("code")
        if script_step
        else "arguments[0].scrollIntoView(); arguments[0].click();"
    )

    driver.execute_script(script_code, login_btn)
    print("✅ 로그인 버튼 클릭 완료")


def main():
    cfg = load_config()
    url = cfg["steps"][0]["value"]
    id_xpath = cfg["id_xpath"]
    pw_xpath = cfg.get("pw_xpath")
    id_js_code = cfg["steps"][3]["code"]
    pw_js_code = cfg["steps"][6]["code"] if pw_xpath else None

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
        driver.execute_script(id_js_code, id_input)
        print("\u2705 ID 입력 완료 (JavaScript 방식)")

        if pw_xpath:
            pw_input = driver.find_element(By.XPATH, pw_xpath)
            if pw_js_code:
                driver.execute_script(pw_js_code, pw_input)
            print("\u2705 비밀번호 입력 완료")

            actions = ActionChains(driver)
            actions.move_to_element(pw_input).click().perform()
            for _ in range(3):
                actions = ActionChains(driver)
                actions.send_keys(Keys.ENTER).perform()
                time.sleep(1)
            print("\u2705 py 비밀번호 입력 후 엔터 3회 입력 (1초 간격)")

        time.sleep(cfg["steps"][-1].get("seconds", 2))
    except Exception as e:
        print(f"Failed to input credentials: {e}")

    input("Login screen displayed. Press Enter to exit...")
    time.sleep(3)
    driver.quit()


if __name__ == '__main__':
    main()
