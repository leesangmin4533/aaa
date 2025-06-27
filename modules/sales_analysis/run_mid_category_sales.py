import json
from selenium import webdriver
from login_runner import run_step, load_env

from pathlib import Path


def parse_ssv(ssv_text):
    blocks = ssv_text.split('\u001e')
    header_line = next(line for line in blocks if 'ITEM_CD' in line)
    col_names = [x.split(':')[0] for x in header_line.split('\u001f')[1:]]

    result = []
    for line in blocks:
        if line.startswith('N\u001f'):
            values = line.split('\u001f')[1:]
            row = {col: values[i] if i < len(values) else '' for i, col in enumerate(col_names)}
            result.append(row)
    return result


def save_filtered_rows(rows, path, fields=["ITEM_CD", "ITEM_NM", "STOCK_QTY"]):
    filtered = [r for r in rows if r.get("STOCK_QTY", "").strip() == "0"]
    lines = [", ".join(r.get(f, "") for f in fields) for r in filtered]

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def run_script(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        steps = json.load(f)["steps"]
    env = load_env()
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    elements = {}
    for step in steps:
        try:
            run_step(driver, step, elements, env)
        except Exception as e:
            print(f"❌ Step failed: {step.get('action')} → {e}")
            break
    driver.quit()

    # 📦 추출된 텍스트 SSV 후처리
    ssv_path = "output/category_001_detail.txt"
    output_path = "output/category_001_filtered.txt"
    if Path(ssv_path).exists():
        with open(ssv_path, "r", encoding="utf-8") as f:
            raw_ssv = f.read()
        rows = parse_ssv(raw_ssv)
        save_filtered_rows(rows, output_path)
        print(f"✅ 필터링된 결과 저장 완료 → {output_path}")
    else:
        print(f"❌ 추출 결과 파일 없음: {ssv_path}")


if __name__ == "__main__":
    run_script("modules/sales_analysis/mid_category_sales_cmd.json")
