**자동발주 프로그램의 브라우저 환경 문서**

---

### 1. 브라우저 종류 및 실행 방식

* **브라우저**: Google Chrome (GUI 모드)
* **실행 옵션**:

  * `--disable-gpu`: GPU 가속 비활성화
  * `--window-size=1920,1080`: 창 해상도 설정
  * `--no-sandbox`: 샌드박스 보안 기능 비활성화
  * `--remote-debugging-port=9222`: Chrome DevTools Protocol(CDP) 연결을 위한 디버깅 포트 오픈

> ✅ 디버깅 포트는 CDP 로그를 활용한 네트워크 요청 감지(`selDetailSearch` 등)에 필수적입니다.

---

### 2. UI 프레임워크: Nexacro 기반 시스템

* Nexacro는 자바스크립트 기반의 웹 UI 프레임워크로, 일반 HTML과 구조 및 ID 체계가 상이함
* 주요 특징:

  * ID에 `.`(dot)이 포함됨 → XPath 사용 시 문자열 그대로 사용해야 함
  * 시각 요소(`:text`, `:icon`)와 기능 요소(`div`, `button`)가 분리되어 있음
  * 클릭 대상은 항상 기능 요소로 지정해야 하며, `:text`는 추출용으로만 사용해야 함

> 예:
>
> * 클릭 대상: `//*[@id="...gridrow_3.cell_3_0"]`
> * 텍스트 추출 대상: `//*[@id="...gridrow_3.cell_3_0:text"]`

---

### 3. 렌더링 및 DOM 구조

* Nexacro는 가상 DOM/가상 스크롤 구조를 사용하여 화면에 보이는 항목만 DOM에 렌더링
* 클릭 전에 해당 항목이 실제로 DOM에 있는지 확인 필요
* 가능한 경우 Nexacro 내부 API (`getRowCount`, `getCellText`)를 사용해 메모리 상 전체 데이터를 직접 조회 가능

---

### 4. 데이터 추출 및 자동화 흐름

* **네트워크 데이터 감지**:

  * DevTools의 CDP 로그를 분석하여 `selDetailSearch` 응답을 감지하고, 해당 SSV 응답을 텍스트로 저장
  * `extract_ssv_from_cdp()` 함수를 통해 수동 없이 저장 가능

* **Selenium 클릭 자동화 흐름**:

  * 로그인 → 메뉴 클릭 → 중분류 row 클릭 → 응답 감지 및 저장 → 조건 필터링 → 반복

---

### 5. 주의 사항 및 안정성 확보 팁

* `:text`, `:icontext`를 클릭 대상으로 사용하면 실패 확률 높음 (기능 요소를 클릭해야 함)
* 요소 등장 여부는 반드시 `WebDriverWait`으로 대기 후 처리할 것
* 각 단계마다 진행 위치 기반 로그(`모듈 > 함수 > 단계`)를 출력하면 디버깅 및 운영 시 매우 유용함

---

### 6. 권장 구조 예시 (폴더/모듈)

```
modules/
├── common/
│   ├── login.py           # 로그인 처리
│   ├── network.py         # CDP 로그 수집 및 SSV 저장
│   └── snippet_utils.py   # XPath → 명령 변환 도구
├── sales_analysis/
│   ├── navigation.py                 # 메뉴 이동
│   ├── mid_category_clicker.py       # 중분류 코드 클릭 기능
│   ├── process_one_category.py       # 단일 항목 처리
│   └── loop_all_categories.py        # 반복 처리
├── data_parser/
│   └── parse_and_save.py  # 필터링 및 저장
main.py                    # 실행 진입점
```

---

이 문서는 자동발주 시스템의 브라우저 기반 구조와 Nexacro UI 대응 방식을 명확히 하기 위해 작성되었습니다.
