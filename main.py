import os
import json
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By


def load_login_url():
    """Return the login page URL from the stored XPath configuration."""
    xpath_path = os.path.join("structure", "login_structure_xpath.json")
    logging.info("Loading login configuration from %s", xpath_path)
    with open(xpath_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    url = cfg["url"]
    logging.info("Loaded login URL: %s", url)
    return url


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    logging.info("Starting login automation")
    url = load_login_url()

    logging.info("Launching Chrome WebDriver")
    driver = webdriver.Chrome()

    logging.info("Navigating to %s", url)
    driver.get(url)

    xpath_path = "/html/body/div/div/div/div[1]/div/div/div[1]/div/div/div/div[1]/div/div[5]/input"
    logging.info("Locating ID input field with XPath: %s", xpath_path)
    try:
        id_input = driver.find_element(By.XPATH, xpath_path)
        logging.info("ID input field found. Clearing any existing text")
        id_input.clear()
        logging.info("Entering ID")
        id_input.send_keys("46513")
        logging.info("ID entered")
        time.sleep(1)
    except Exception as exc:
        logging.exception("Failed to enter ID: %s", exc)

    input("Login screen displayed. Press Enter to exit...")

    logging.info("Closing browser in 3 seconds")
    time.sleep(3)
    driver.quit()
    logging.info("Browser closed")


if __name__ == '__main__':
    main()
