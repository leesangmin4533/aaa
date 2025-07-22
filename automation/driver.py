from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from .config import log


def create_driver() -> Any:
    """Create and configure a Chrome WebDriver instance."""
    options = Options()
    options.add_experimental_option("detach", True)
    options.add_argument("--disk-cache-size=0")
    caps = DesiredCapabilities.CHROME.copy()
    caps["goog:loggingPrefs"] = {"browser": "ALL"}
    for key, value in caps.items():
        options.set_capability(key, value)
    driver = webdriver.Chrome(service=Service(), options=options)
    # Set timeouts generously as the caller may adjust them later
    driver.set_script_timeout(3600)
    driver.command_executor.set_timeout(3600)
    log.debug("Chrome driver created", extra={"tag": "driver"})
    return driver
