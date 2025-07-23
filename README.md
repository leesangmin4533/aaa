# BGF Retail Automation (Nexacro-Optimized)

이 저장소는 BGF 리테일 시스템의 "중분류별 매출 구성비" 페이지 데이터 수집을 자동화하는 프로젝트입니다. Nexacro API를 직접 활용하여 안정성과 속도를 높이는 데 중점을 두었습니다.

## 주요 기능

- **안정적인 데이터 수집**: 화면의 HTML을 파싱하는 대신, Nexacro의 내부 데이터 저장소인 `Dataset`에 직접 접근하여 데이터를 빠르고 정확하게 수집합니다.
- **지능적인 동기화**: `delay`를 사용한 무작정 대기 대신, 데이터 통신 완료 시점을 알려주는 트랜잭션 콜백(Callback)을 활용하여 불필요한 대기 시간을 제거하고 신뢰성을 높였습니다.
- **날짜별 DB 관리**: 데이터는 날짜별로 독립된 DB 파일(예: `20250718.db`)에 저장됩니다. 날짜가 바뀌면 새로운 DB 파일이 생성됩니다.
- **중복 방지 및 데이터 검증**: 
  - 동일 날짜/상품 코드의 데이터는 sales 증가 시에만 저장
  - 수집 시각은 분 단위까지 정확히 기록 (YYYY-MM-DD HH:MM)
- **자동 과거 데이터 수집**: `main.py` 실행 시, 최근 7일 중 누락된 날짜의 데이터를 자동으로 수집합니다.
- **자동 로그인 및 팝업 처리**: 설정된 정보를 통해 자동으로 로그인하고, 과정에서 나타나는 팝업을 닫습니다.

## 설정

### 1. `config.json`

프로젝트의 주요 설정은 루트 디렉토리의 `config.json` 파일을 통해 관리됩니다.

```json
{
    "db_file": "code_outputs/integrated_sales.db",
    "scripts": {
        "automation_library": "nexacro_automation_library.js",
        "navigation": "navigation.js"
    },
    "field_order": [
        "midCode", "midName", "productCode", "productName", 
        "sales", "order_cnt", "purchase", "disposal", "stock"
    ],
    "timeouts": {
        "page_load": 120
    }
}
```

- `db_file`: 모든 데이터가 저장될 통합 SQLite DB 파일 경로입니다.
- `scripts`: 자동화에 사용될 JavaScript 파일 목록입니다.
  - `automation_library`: 핵심 데이터 수집 로직이 담긴 Nexacro 최적화 라이브러리입니다.
  - `navigation`: 목표 페이지로 이동하는 스크립트입니다.

### 2. 로그인 정보

로그인 정보는 `.env` 파일 또는 시스템 환경 변수를 통해 설정할 수 있습니다.

- **`.env` 파일 (권장)**: 프로젝트 루트에 `.env` 파일을 만들고 아래와 같이 작성합니다.
  ```env
  BGF_USER_ID=your_id
  BGF_PASSWORD=your_password
  ```

## 사용법

필요한 Python 라이브러리를 설치한 후, 다음 명령어로 자동화를 시작합니다.

```bash
python -m aaa
# 또는
python main.py
```

`main.py`는 다음 순서로 작업을 수행합니다.

1.  **과거 데이터 확인**: 통합 DB에 최근 7일치 데이터 중 누락된 날짜가 있는지 확인합니다.
2.  **과거 데이터 수집**: 누락된 날짜가 있다면, 가장 오래된 날짜부터 순서대로 해당 날짜의 데이터 수집 사이클을 실행합니다.
3.  **현재 데이터 수집**: 과거 데이터 처리가 끝나면, 오늘 날짜의 데이터 수집 사이클을 실행합니다.

각 수집 사이클(`_run_collection_cycle`)은 다음처럼 동작합니다.
- Chrome 드라이버를 실행하고 로그인합니다.
- `navigation.js`를 실행하여 목표 페이지로 이동합니다.
- `nexacro_automation_library.js`를 브라우저에 주입하고, `window.automation.runCollectionForDate('YYYYMMDD')` 함수를 호출하여 데이터 수집을 시작합니다.
- 수집된 데이터는 통합 DB에 저장됩니다.

## 데이터베이스 구조

`mid_sales` 테이블에 데이터가 저장되며, 중복 저장을 방지하기 위한 제약 조건이 포함되어 있습니다.

```sql
CREATE TABLE IF NOT EXISTS mid_sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collected_at TEXT,        -- 수집 시간 (YYYY-MM-DD HH:MM)
    mid_code TEXT,           -- 중분류 코드
    mid_name TEXT,           -- 중분류명
    product_code TEXT,       -- 상품 코드
    product_name TEXT,       -- 상품명
    sales INTEGER,           -- 매출액
    order_cnt INTEGER,       -- 주문수량
    purchase INTEGER,        -- 매입액
    disposal INTEGER,        -- 폐기액
    stock INTEGER,           -- 재고액
    UNIQUE(collected_at, product_code) -- 이 조합은 고유해야 함
);
```

## 자동화 스크립트 상세 (`nexacro_automation_library.js`)

이 프로젝트의 핵심은 DOM 요소를 직접 제어하는 대신 Nexacro 프레임워크의 내부 API를 활용하는 것입니다.

- **`Dataset` 직접 접근**: 화면에 보이는 그리드(Grid)의 HTML을 읽는 대신, 그리드에 연결된 내부 데이터 저장소(`Dataset`)에 직접 접근합니다. 이를 통해 스크롤 없이 모든 데이터를 한 번에, 빠르고 정확하게 가져올 수 있습니다.
- **트랜잭션 콜백 기반 동기화**: `delay()`를 사용한 대기 대신, Nexacro의 데이터 통신(Transaction) 완료 신호(`fn_callback`)를 감지하여, 데이터 로딩이 완료되는 정확한 시점에 다음 동작을 수행합니다.
- **안정적인 컴포넌트 제어**: `lookup()`, `set_rowposition()`, `triggerEvent()` 등 Nexacro 내부 API를 사용하여 컴포넌트를 안정적으로 제어합니다.
## 프로젝트 요약
자세한 요약은 PROJECT_SUMMARY.txt 파일을 참조하세요.
