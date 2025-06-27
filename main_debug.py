from selenium import webdriver
from login_runner import run_login, run_step, load_env
import json


def run_sales_analysis(driver):
    # 디버깅용 명령문 경로로 변경됨
    with open("modules/sales_analysis/mid_category_sales_cmd_debug.json", "r", encoding="utf-8") as f:
        steps = json.load(f)["steps"]
    env = load_env()
    elements = {}
    for step in steps:
        try:
            run_step(driver, step, elements, env)
        except Exception as e:
            print(f"❌ Sales analysis step failed: {step.get('action')} → {e}")
            break


def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--remote-debugging-port=9222")
    # options.add_argument("--headless=new")  # headless 환경에서 실행 가능

    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

    driver = webdriver.Chrome(options=options)  # ✅ 자동 드라이버 탐색
    run_login(driver)
    run_sales_analysis(driver)

    from parse_and_save import parse_ssv, save_filtered_rows
    from pathlib import Path

    ssv_path = "output/category_001_detail.txt"
    out_path = "output/category_001_filtered.txt"
    if Path(ssv_path).exists():
        with open(ssv_path, "r", encoding="utf-8") as f:
            rows = parse_ssv(f.read())
        save_filtered_rows(rows, out_path)
        print(f"✅ 필터링 완료: {out_path}")
    else:
        print(f"❌ 추출 결과 파일 없음: {ssv_path}")

    input("⏸ 로그인 화면 유지 중. Enter를 누르면 종료됩니다.")
    driver.quit()


if __name__ == "__main__":
    main()
