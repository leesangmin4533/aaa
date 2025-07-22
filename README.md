# BGF Retail Automation

이 저장소는 BGF 리테일 시스템을 자동화하기 위한 실습용 코드 모음입니다. `main.py`를 실행하여 중분류별 매출 데이터를 수집하고 SQLite 데이터베이스에 저장할 수 있습니다.

## 주요 기능

- **자동 로그인:** `.env` 또는 `config.json` 파일의 정보를 사용하여 BGF 리테일 시스템에 자동으로 로그인합니다.
- **데이터 수집:** "중분류별 매출 구성비" 페이지에서 모든 중분류 및 상품 데이터를 자동으로 수집합니다.
- **데이터베이스 저장:** 수집된 데이터는 `code_outputs/YYYYMMDD.db` 형태의 SQLite 파일에 저장됩니다.
- **과거 데이터 수집:** `main.py` 실행 시 최근 7일치 데이터가 없으면 자동으로 과거 데이터를 수집합니다.
- **팝업 자동 닫기:** 로그인 및 페이지 이동 시 나타나는 팝업을 자동으로 닫습니다.
- **수량 검증:** 중분류의 '판매수량'과 해당 중분류에 속한 상품들의 '매출' 수량 합계를 비교하여 데이터 수집의 정확성을 검증합니다.

## 설정

### 1. `config.json`

프로젝트의 주요 설정은 루트 디렉토리의 `config.json` 파일을 통해 관리됩니다. 주요 설정 항목은 다음과 같습니다.

- `db_file`: 데이터가 저장될 SQLite 데이터베이스 파일 이름
- `past7_db_file`: 과거 7일치 데이터가 저장될 데이터베이스 파일 이름
- `scripts`: 자동화에 사용될 JavaScript 파일 이름 (navigation, default, listener)
- `field_order`: 수집할 데이터의 필드 순서
- `timeouts`: 페이지 로드 및 데이터 수집 타임아웃 설정

### 2. 로그인 정보

로그인 정보는 다음 세 가지 방법 중 하나로 설정할 수 있습니다.

1.  **`.env` 파일:** 프로젝트 루트에 `.env` 파일을 만들고 다음과 같이 작성합니다.

    ```env
    BGF_USER_ID=your_id
    BGF_PASSWORD=your_password
    ```

2.  **환경 변수:** 시스템 환경 변수 `BGF_USER_ID`와 `BGF_PASSWORD`를 설정합니다.

3.  **자격 증명 파일:** `config.json`에 `credential_file` 경로를 지정하고, 해당 경로에 JSON 형식의 자격 증명 파일을 생성합니다.

    ```json
    {
      "id": "YOUR_ID",
      "password": "YOUR_PASSWORD"
    }
    ```

## 사용법

필요한 라이브러리를 설치한 후, 다음 명령어로 자동화를 시작할 수 있습니다.

```bash
python -m aaa  # 또는 python main.py
```

`main.py`는 다음 순서로 작업을 수행합니다.

1.  Chrome 드라이버를 실행하고 로그인합니다.
2.  `scripts/navigation.js`를 실행하여 "중분류별 매출 구성비" 페이지로 이동합니다.
3.  `scripts/auto_collect_mid_products.js`와 `scripts/data_collect_listener.js`를 실행하여 데이터 수집을 시작합니다.
4.  `auto_collect_mid_products.js`가 중분류와 상품을 순차적으로 클릭하면, `data_collect_listener.js`가 `mid-clicked` 이벤트를 감지하여 `window.automation.liveData` 배열에 데이터를 누적합니다.
5.  `main.py`는 주기적으로 `window.automation.parsedData` (또는 `liveData`)를 읽어와 `code_outputs/YYYYMMDD.db` 파일에 저장합니다.

## 데이터베이스 구조

`mid_sales` 테이블에 데이터가 저장되며, 구조는 다음과 같습니다.

```sql
id INTEGER PRIMARY KEY AUTOINCREMENT,
collected_at TEXT, -- 수집 시간 (YYYY-MM-DD HH:MM)
mid_code TEXT,
mid_name TEXT,
product_code TEXT,
product_name TEXT,
sales INTEGER,
order_cnt INTEGER,
purchase INTEGER,
disposal INTEGER,
stock INTEGER
```

## 팝업 처리

`utils/popup_util.py`의 `close_all_modals` 함수는 로그인 직후나 화면 이동 시 나타날 수 있는 여러 팝업을 자동으로 닫는 역할을 합니다. 이 함수는 '닫기', '확인' 등의 텍스트를 가진 버튼이나 미리 정의된 ID 목록을 순회하며 클릭을 시도합니다.

최근 "본부매가 자동반영 알림 메세지" 팝업(`STZZ210_P0`)과 "재택 유선권장 안내" 팝업(`STZZ120_P0`)이 자동으로 닫히도록 관련 ID가 추가되었습니다.

새로운 팝업을 처리해야 할 경우, `popup_util.py` 내 `js_script` 변수 안의 `idSelectors` 배열에 해당 팝업의 닫기/확인 버튼 ID를 추가하면 됩니다.

## 데이터 수집 최적화

데이터 수집 속도 향상을 위해 `scripts/auto_collect_mid_products.js` 파일의 대기 시간이 최적화되었습니다. `MutationObserver`를 활용하여 DOM 변경을 감지하고, 불필요한 고정 대기 시간을 단축하여 안정성을 유지하면서도 더 빠른 데이터 수집이 가능해졌습니다.

## 데이터가 수집되지 않을 때

수집 스크립트 실행 후 데이터가 수집되지 않으면 브라우저 콘솔 로그를 확인해 보세요. `main.py`는 데이터가 없을 경우 `driver.get_log("browser")` 결과와 `window.automation.error` 값을 출력하므로 오류 메시지를 통해 문제 원인을 파악할 수 있습니다.

---

## 자동화 스크립트 개선 (2025-07-22)

기존의 자동화 스크립트(`auto_collect_past_7days.js`, `auto_collect_mid_products.js`)를 **Nexacro 프레임워크 API 중심의 접근 방식으로 전면 개편**하여 하나의 파일로 통합했습니다. 이를 통해 자동화의 안정성, 속도, 유지보수성을 크게 향상했습니다.

**새로운 통합 라이브러리:** `scripts/nexacro_automation_library.js`

### 주요 개선 내용

1.  **`Dataset` 직접 접근**:
    *   **변경 전**: 화면에 보이는 그리드(Grid)의 HTML 요소(`innerText`)를 직접 읽어 데이터를 수집했습니다. 이 방식은 UI가 조금만 변경되어도 스크립트가 쉽게 깨지는 단점이 있었습니다.
    *   **변경 후**: Nexacro의 내부 데이터 저장소인 `Dataset`에 직접 접근하여 데이터를 가져옵니다. 이는 화면 렌더링과 무관하게 원본 데이터를 즉시 가져오므로 매우 빠르고 안정적입니다.

2.  **트랜잭션 콜백(Callback) 기반 동기화**:
    *   **변경 전**: `delay()` 함수를 사용하여 정해진 시간만큼 기다리는 방식을 사용했습니다. 이는 네트워크 속도에 따라 불필요하게 오래 기다리거나, 로딩이 끝나기 전에 다음 동작으로 넘어가 오류를 발생시킬 수 있었습니다.
    *   **변경 후**: Nexacro의 데이터 통신(Transaction)이 완료될 때 발생하는 콜백 함수(`fn_callback`)를 감지하여, 데이터 로딩이 완료되는 정확한 시점에 다음 단계를 진행합니다. 이를 통해 불필요한 대기 시간을 없애고 실행 신뢰도를 높였습니다.

3.  **안정적인 컴포넌트 제어 및 스크롤 로직 개선**:
    *   `lookup()` API를 사용하여 컴포넌트를 안정적으로 찾습니다.
    *   스크롤 버튼을 반복적으로 클릭하는 대신, `Dataset`에서 전체 목록을 가져와 처리하므로 더 이상 불완전한 스크롤 로직이 필요하지 않습니다.
    *   그리드의 특정 행을 선택할 때도 `set_rowposition()`과 `triggerEvent()` 같은 Nexacro 내부 API를 사용하여 실제 사용자의 클릭과 동일한 이벤트를 안정적으로 발생시킵니다.

### 사용법 변경

이제 자동화 실행 시, `main.py`는 새로운 `nexacro_automation_library.js` 파일을 브라우저에 주입한 후, 아래 함수를 호출하여 데이터 수집을 시작해야 합니다.

```javascript
window.automation.runCollectionForDate('YYYYMMDD');
```

이 함수는 지정된 날짜의 데이터 수집 전 과정을 책임지고 수행하며, 수집이 완료되면 결과는 `window.automation.parsedData`에 저장됩니다.
