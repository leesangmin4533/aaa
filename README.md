# BGF Retail Automation

이 저장소는 BGF 리테일 시스템을 자동화하기 위한 실습용 코드 모음입니다. `analysis` 모듈에서 제공하는 함수들을 이용해 간단한 화면 전환이나 데이터 추출 작업을 수행할 수 있습니다.

다음은 중분류별 매출구성비 화면으로 이동하는 예시입니다.

```python
from selenium.webdriver.remote.webdriver import WebDriver
from analysis import (
    navigate_to_category_mix_ratio,
    extract_product_info,
    export_product_data,
)
import time

# driver는 로그인 이후의 WebDriver 인스턴스라고 가정합니다.
if navigate_to_category_mix_ratio(driver):
    print("화면 이동 성공")

    # 원하는 중분류 코드를 찾아 클릭한다.
    driver.execute_script(
        """const cell = [...document.querySelectorAll("div[id*='gdList.body'][id$='_0:text']")].find(el => el.innerText.trim() === '201');
if (cell) {
    const target = document.getElementById(cell.id.replace(':text', ''));
    if (target) target.click();
}
"""
        )

    # 상품 셀이 렌더링될 때까지 최대 2초간 대기한다.
    for _ in range(10):
        exists = driver.execute_script(
            "return document.querySelector(\"div[id*='gdDetail.body'][id*='cell_0_0'][id$=':text']\") !== null;"
        )
        if exists:
            break
        time.sleep(0.2)

    # 상품 데이터를 추출해 현재 디렉터리에 저장
    rows = extract_product_info(driver) or []
    export_product_data(rows)
else:
    print("화면 이동 실패")
```
