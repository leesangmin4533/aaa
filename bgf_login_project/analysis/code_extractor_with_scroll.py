from selenium.webdriver.common.by import By
import time
import os


def _click_code_and_get_detail(driver, code_str):
    """Click the given code row and return the detail text."""
    code_xpath = f"//div[text()='{code_str}' and contains(@id, 'gdList.body')]"
    code_el = driver.find_element(By.XPATH, code_xpath)
    if not code_el.is_displayed():
        return None

    code_el.click()
    time.sleep(0.5)

    detail_xpath = "//div[contains(@id, 'gdDetail.body.gridrow_0.cell_0_0:text')]"
    detail_el = driver.find_element(By.XPATH, detail_xpath)
    return detail_el.text.strip()


def extract_code_details_with_scroll(driver, output_file="code_outputs/all_codes.txt"):
    """Extract details for codes 001~900 using scroll support and save to one file."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    scroll_pos = 0
    scroll_step = 5
    scroll_max = driver.execute_script(
        """
        return nexacro.getApplication()
            .mainframe.HFrameSet00.VFrameSet00.FrameSet
            .STMB011_M0.form.div_workForm.form.div2.form.gdList.vscrollbar.max;
        """
    )

    seen_codes = set()

    with open(output_file, "w", encoding="utf-8") as out:
        for attempt in range(200):
            for code in range(1, 901):
                code_str = f"{code:03}"
                if code_str in seen_codes:
                    continue
                try:
                    detail_text = _click_code_and_get_detail(driver, code_str)
                    if detail_text:
                        out.write(f"{code_str},{detail_text}\n")
                        seen_codes.add(code_str)
                except Exception:
                    continue

            scroll_pos += scroll_step
            if scroll_pos > scroll_max:
                break

            driver.execute_script(
                f"""
                nexacro.getApplication()
                    .mainframe.HFrameSet00.VFrameSet00.FrameSet
                    .STMB011_M0.form.div_workForm.form.div2.form.gdList.vscrollbar.set_pos({scroll_pos});
                """
            )
            time.sleep(1)
