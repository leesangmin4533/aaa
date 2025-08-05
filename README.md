# BGF Retail Automation (Nexacro-Optimized)

이 저장소는 BGF 리테일 시스템의 "중분류별 매출 구성비" 페이지 데이터 수집을 자동화하는 프로젝트입니다. Nexacro API를 직접 활용하여 안정성과 속도를 높이는 데 중점을 두었으며, 여러 점포의 데이터를 순차적으로 처리합니다.

## 주요 기능

- **여러 점포 자동화**: `config.json`에 정의된 각 점포(예: Hoban, Dongyang)에 대해 순차적으로 로그인하고 데이터를 수집합니다.
- **안정적인 데이터 수집**: 화면의 HTML을 파싱하는 대신, Nexacro의 내부 데이터 저장소인 `Dataset`에 직접 접근하여 데이터를 빠르고 정확하게 수집합니다.
- **지능적인 동기화**: `delay` 대신 트랜잭션 콜백을 활용하여 불필요한 대기 시간을 제거하고 신뢰성을 높였습니다.
- **점포별 DB 관리**: 각 점포별로 단일 SQLite DB(`hoban.db`, `dongyang.db` 등)에 날짜별 데이터가 누적 저장됩니다.
- **중복 방지 및 데이터 검증**:
  - 동일 날짜/상품 코드의 데이터는 sales 증가 시에만 저장
  - 수집 시각은 분 단위까지 정확히 기록 (YYYY-MM-DD HH:MM)
- **자동 과거 데이터 수집**: 최근 7일 중 누락된 날짜의 데이터를 자동으로 보충합니다.
- **판매량 예측**: 수집한 데이터를 기반으로 중분류별 판매량을 예측하고 추천 상품 조합을 저장합니다.
- **자동 로그인 및 팝업 처리**: 설정된 정보를 통해 자동으로 로그인하고, 과정에서 나타나는 팝업을 닫습니다.

## 설정

### 1. `config.json`

프로젝트의 주요 설정은 루트 디렉토리의 `config.json` 파일을 통해 관리됩니다.

```json
{
    "stores": {
        "hoban": {
            "db_file": "code_outputs/db/hoban.db",
            "credentials_env": {
                "id": "BGF_HOBAN_ID",
                "password": "BGF_HOBAN_PW"
            }
        },
        "dongyang": {
            "db_file": "code_outputs/db/dongyang.db",
            "credentials_env": {
                "id": "BGF_DONGYANG_ID",
                "password": "BGF_DONGYANG_PW"
            }
        }
    },
    "scripts": {
        "default": "nexacro_automation_library.js",
        "listener": "data_collect_listener.js",
        "navigation": "navigation.js"
    },
    "field_order": [
        "midCode", "midName", "productCode", "productName",
        "sales", "order_cnt", "purchase", "disposal", "stock"
    ],
    "timeouts": {
        "data_collection": 300,
        "page_load": 120
    },
    "cycle_interval_seconds": 60,
    "log_file": "logs/automation.log"
}
```

- `stores`: 수집 대상 점포와 각 점포의 DB 파일 및 환경 변수 키를 정의합니다.
- `scripts`: 자동화에 사용될 JavaScript 파일 목록입니다.
  - `default`: 핵심 데이터 수집 로직이 담긴 Nexacro 최적화 라이브러리입니다.
  - `listener`: 실시간 DOM 변화를 감지하여 데이터를 수집하는 스크립트입니다.
  - `navigation`: 목표 페이지로 이동하는 스크립트입니다.
  - `date_changer.js`는 내부적으로 로드되어 날짜를 변경합니다.

### JSON 구조화 로그

프로젝트의 모든 로그는 JSON 형식으로 기록되며 `timestamp`, `level`, `message`, `store_id`, `logger`, `tag` 필드를 포함합니다. 로그 파일 경로는 환경 변수 `LOG_FILE` 또는 `config.json`의 `log_file` 값으로 지정할 수 있습니다. 점포별 로그를 남기려면 `get_logger("bgf_automation", store_id="hoban")`처럼 `store_id`를 전달합니다.

### 2. 로그인 정보

로그인 정보는 `.env` 파일 또는 시스템 환경 변수를 통해 설정할 수 있습니다.

- **`.env` 파일 (권장)**: 프로젝트 루트에 `.env` 파일을 만들고 아래와 같이 작성합니다.
  ```env
  BGF_HOBAN_ID=your_id
  BGF_HOBAN_PW=your_password
  BGF_DONGYANG_ID=other_id
  BGF_DONGYANG_PW=other_password
  ```

## 사용법

먼저 아래 명령어로 프로젝트 의존성을 설치합니다.

```bash
pip install -r requirements.txt
pip install pytest
```

이후 자동화를 시작합니다.

```bash
python -m aaa
# 또는
python main.py
```

`main.py`는 `config.json`에 정의된 모든 점포에 대해 아래 과정을 순차적으로 수행합니다.

1.  **과거 데이터 확인**: 점포별 DB에서 최근 7일 중 누락된 날짜를 확인합니다.
2.  **과거 데이터 수집**: 누락된 날짜가 있다면, 가장 오래된 날짜부터 순서대로 해당 날짜의 데이터를 수집합니다.
3.  **오늘 데이터 수집**: 현재 날짜의 데이터를 수집합니다.
4.  **판매량 예측**: 중분류별 판매량을 예측하고 추천 상품 조합을 별도 DB에 저장합니다.

각 수집 사이클은 다음처럼 동작합니다.
- Chrome 드라이버를 실행하고 로그인합니다.
- `nexacro_automation_library.js`와 `date_changer.js`를 브라우저에 주입합니다.
- `navigation.js`를 실행하여 목표 페이지로 이동합니다.
- `window.automation.runCollectionForDate('YYYYMMDD')` 함수를 호출하여 데이터 수집을 시작합니다.
- 수집된 데이터는 점포별 DB에 저장됩니다.

## 의존성 설치

프로젝트에서 필요한 패키지는 `requirements.txt`와 `dev-requirements.txt`에 정의되어 있습니다. 다음 명령어로 설치합니다.

```bash
pip install -r requirements.txt -r dev-requirements.txt
```

## 테스트 실행

아래 단계에 따라 테스트를 실행할 수 있습니다.

1. **의존성 설치**
   ```bash
   pip install -r requirements.txt -r dev-requirements.txt
   ```
2. **환경 변수 설정**
   - 기상청 API를 사용하는 테스트를 위해 `KMA_API_KEY`를 설정해야 합니다.
   - 예시
     ```bash
     # macOS/Linux
     export KMA_API_KEY=your_api_key
     # Windows PowerShell
     set KMA_API_KEY=your_api_key
     ```
3. **테스트 실행**
   ```bash
   pytest
   ```

### 실행 예시

- **로컬 실행**
  ```bash
  pip install -r requirements.txt -r dev-requirements.txt
  export KMA_API_KEY=your_api_key
  pytest
  ```

- **GitHub Actions**
  ```yaml
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.x"
  - run: pip install -r requirements.txt -r dev-requirements.txt
  - run: pytest
    env:
      KMA_API_KEY: ${{ secrets.KMA_API_KEY }}
  ```

## 데이터 포맷

JavaScript 스크립트에서 수집한 각 상품 데이터는 다음과 같은 필드를 포함한 객체 형태로 Python에 전달됩니다.

| 키 이름        | 설명             |
|----------------|------------------|
| `midCode`      | 중분류 코드      |
| `midName`      | 중분류명         |
| `productCode`  | 상품 코드        |
| `productName`  | 상품명           |
| `sales`        | 매출액           |
| `order_cnt`    | 주문수량         |
| `purchase`     | 매입액           |
| `disposal`     | 폐기액           |
| `stock`        | 재고액           |
| `soldout`      | 품절 수량        |

`write_sales_data` 함수는 위 필드명 외에도 `snake_case` 형태(`mid_code` 등)나 기존 텍스트 파일 포맷(`order`, `discard`)을 허용합니다.

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
    soldout INTEGER,         -- 품절 수량
    weekday INTEGER,         -- 요일
    month INTEGER,           -- 월
    week_of_year INTEGER,    -- 주차
    is_holiday INTEGER,      -- 공휴일/토요일 여부
    temperature REAL,        -- 기온
    rainfall REAL,           -- 강수량
    UNIQUE(collected_at, product_code) -- 이 조합은 고유해야 함
);
```

## DB 마이그레이션

기존 데이터베이스에 `soldout` 컬럼이 없다면 아래 스크립트를 실행하여 컬럼을 추가하고 공휴일 정보를 최신 규칙으로 갱신하세요.

```bash
python update_db_script.py
```

## 자동화 스크립트 상세 (`nexacro_automation_library.js`)

이 프로젝트의 핵심은 DOM 요소를 직접 제어하는 대신 Nexacro 프레임워크의 내부 API를 활용하는 것입니다.

- **`Dataset` 직접 접근**: 화면에 보이는 그리드(Grid)의 HTML을 읽는 대신, 그리드에 연결된 내부 데이터 저장소(`Dataset`)에 직접 접근합니다. 이를 통해 스크롤 없이 모든 데이터를 한 번에, 빠르고 정확하게 가져올 수 있습니다.
- **트랜잭션 콜백 기반 동기화**: `delay()`를 사용한 대기 대신, Nexacro의 데이터 통신(Transaction) 완료 신호(`fn_callback`)를 감지하여, 데이터 로딩이 완료되는 정확한 시점에 다음 동작을 수행합니다.
- **안정적인 컴포넌트 제어**: `lookup()`, `set_rowposition()`, `triggerEvent()` 등 Nexacro 내부 API를 사용하여 컴포넌트를 안정적으로 제어합니다.
## 프로젝트 요약
자세한 요약은 PROJECT_SUMMARY.txt 파일을 참조하세요.

더 자세한 실행 흐름은 `BGF_Automation_Flow.md` 문서를 참고하세요. 정기 실행이 필요하다면 `python scheduler/scheduler.py`로 스케줄러를 실행할 수 있습니다.
