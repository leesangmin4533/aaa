from selenium import webdriver


def create_chrome_driver(headless: bool = False) -> webdriver.Chrome:
    """Return a Chrome WebDriver with common options enabled."""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--remote-debugging-port=9222")
    if headless:
        options.add_argument("--headless=new")
    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    return webdriver.Chrome(options=options)
