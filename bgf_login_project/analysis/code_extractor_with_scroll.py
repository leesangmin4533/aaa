from selenium.webdriver.common.by import By
import time
import os


def _click_code_and_get_detail(driver, code_str, max_attempts: int = 2):
    """주어진 코드 행을 클릭하고 세부 정보를 반환합니다.

    클릭 전 요소 존재 여부를 재확인하고 JavaScript 방식으로 클릭한다.
    """
    code_xpath = f"//div[text()='{code_str}' and contains(@id, 'gdList.body')]"

    for _ in range(max_attempts):
        try:
            code_el = driver.find_element(By.XPATH, code_xpath)
            if not code_el.is_displayed():
                raise Exception("code not visible yet")
            driver.execute_script("arguments[0].click();", code_el)
            break
        except Exception:
            time.sleep(0.5)
    else:
        return None

    time.sleep(0.5)

    detail_xpath = "//div[contains(@id, 'gdDetail.body.gridrow_0.cell_0_0:text')]"
    detail_el = driver.find_element(By.XPATH, detail_xpath)
    return detail_el.text.strip()


def extract_code_details_with_button_scroll(driver, output_file="code_outputs/all_codes.txt"):
    """inc 버튼 클릭으로 스크롤하며 코드 001~900의 세부 정보를 추출합니다."""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as out:
        for code in range(1, 901):
            code_str = f"{code:03}"
            try:
                detail_text = _click_code_and_get_detail(driver, code_str)
                if detail_text:
                    out.write(f"{code_str},{detail_text}\n")
            except Exception as e:
                print(f"[ERROR] Code {code_str}: {e}")
            finally:
                try:
                    driver.execute_script(
                        """
                        document.querySelector("div[id$='gdList.vscrollbar.incbutton:icontext']").click();
                        """
                    )
                except Exception as e:
                    print(f"[SCROLL ERROR] after code {code_str}: {e}")
                time.sleep(1.5)
