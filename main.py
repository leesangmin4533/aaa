from selenium import webdriver
from login_runner import run_login


def main():
    driver = webdriver.Chrome()
    run_login(driver)

    input("⏸ 로그인 화면 유지 중. Enter를 누르면 종료됩니다.")
    driver.quit()


if __name__ == "__main__":
    main()
