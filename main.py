import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By


def load_login_url():
    """Return the login page URL from the stored XPath configuration."""
    xpath_path = os.path.join("structure", "login_structure_xpath.json")
    with open(xpath_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg["url"]


def main():
    url = load_login_url()
    driver = webdriver.Chrome()
    driver.get(url)
    # Automatically fill the ID field using the latest XPath configuration.
    xpath_path = "/html/body/div/div/div/div[1]/div/div/div[1]/div/div/div/div[1]/div/div[5]/input"
    try:
        id_input = driver.find_element(By.XPATH, xpath_path)
        id_input.clear()
        id_input.send_keys("46513")
    except Exception:
        pass
    input("Login screen displayed. Press Enter to exit...")
    driver.quit()


if __name__ == '__main__':
    main()
