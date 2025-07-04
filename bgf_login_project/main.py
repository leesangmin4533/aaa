from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from login.login_bgf import login_bgf

def create_driver():
    options = Options()
    options.add_experimental_option("detach", True)
    return webdriver.Chrome(service=Service(), options=options)

if __name__ == "__main__":
    driver = create_driver()
    login_bgf(driver)
