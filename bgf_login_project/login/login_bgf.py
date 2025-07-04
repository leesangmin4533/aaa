from selenium.webdriver.remote.webdriver import WebDriver
import time

from utils.log_util import create_logger
log = create_logger("login_bgf")

def login_bgf(driver: WebDriver):
    url = "https://store.bgfretail.com/websrc/deploy/index.html"
    driver.get(url)
    time.sleep(3)  # Nexacro 로딩 대기

    js = """
    try {
        var form = window.mainframe.form.LoginFrame.form.div_login.form;

        form.edt_id.set_value("46513");
        form.edt_id.oneditchanged();  // 입력 이벤트 강제 발생

        form.edt_pw.set_value("1113");
        form.edt_pw.oneditchanged();

        form.btn_login.click();
        form.btn_login.onclick();     // 클릭 이벤트 직접 발생
    } catch (e) {
        console.error("로그인 실패:", e);
    }
    """
    try:
        driver.execute_script(js)
        log("login", "완료", "로그인 스크립트 실행됨")
    except Exception as e:
        log("login", "오류", f"JS 실행 실패: {e}")
    time.sleep(5)  # 로그인 처리 기다림
