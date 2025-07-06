from selenium.webdriver.common.by import By
import os
import time


def extract_code_details(driver, output_dir="code_outputs"):
    """Iterate codes from 001 to 900, open detail and save product code text."""
    os.makedirs(output_dir, exist_ok=True)

    for code in range(1, 901):
        code_str = f"{code:03}"
        try:
            code_xpath = f"//div[text()='{code_str}' and contains(@id, 'gdList.body')]"
            code_el = driver.find_element(By.XPATH, code_xpath)
            if not code_el.is_displayed():
                continue
            code_el.click()
            time.sleep(1)

            detail_xpath = "//div[contains(@id, 'gdDetail.body.gridrow_0.cell_0_0:text')]"
            detail_el = driver.find_element(By.XPATH, detail_xpath)
            detail_text = detail_el.text.strip()

            if detail_text:
                filepath = os.path.join(output_dir, f"code_{code_str}.txt")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(detail_text)
        except Exception:
            continue
