from selenium import webdriver
from login_runner import run_login


def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")  # Best practice: headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    run_login(driver)

    input("⏸ 로그인 화면 유지 중. Enter를 누르면 종료됩니다.")
    driver.quit()


if __name__ == "__main__":
    main()
