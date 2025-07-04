from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

from utils.log_util import create_logger

log = create_logger("login_bgf")

def login_bgf(driver):
    url = "https://store.bgfretail.com/websrc/deploy/index.html"
    driver.get(url)
    time.sleep(2)
    try:
        id_input = driver.find_element(By.ID, "userId")
        pw_input = driver.find_element(By.ID, "userPw")
        id_input.send_keys("46513")
        pw_input.send_keys("1113")
        pw_input.send_keys(Keys.ENTER)
        log("login", "완료", "로그인 시도 완료")
        time.sleep(2)
    except Exception as e:
        log("login", "오류", f"로그인 실패 또는 요소 없음: {e}")
