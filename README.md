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

# driver는 로그인 이후의 WebDriver 인스턴스라고 가정합니다.
if navigate_to_category_mix_ratio(driver):
    print("화면 이동 성공")
else:
    print("화면 이동 실패")

# 상품 데이터를 추출해 현재 디렉터리에 저장
rows = extract_product_info(driver) or []
export_product_data(rows)
```
