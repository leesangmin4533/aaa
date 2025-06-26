import os
import json
from selenium import webdriver


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
    input("Login screen displayed. Press Enter to exit...")
    driver.quit()


if __name__ == '__main__':
    main()
