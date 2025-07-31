# BGF 자동화 프로젝트: 주요 흐름 및 아키텍처

이 문서는 BGF 자동화 프로젝트의 전반적인 데이터 수집 및 처리 흐름을 설명합니다.

## 1. 실행 순서

1. **시작**: 사용자가 `python main.py`를 실행합니다.
2. **로그 초기화**: `utils/log_util.py`가 `logs/automation.log` 파일을 매 실행 시 새로 만듭니다.
3. **드라이버 생성**: `main.py`에서 Selenium WebDriver 인스턴스를 생성합니다.
4. **로그인 및 팝업 처리**: `login/login_bgf.py`로 로그인 후 `utils/popup_util.py`로 팝업을 닫습니다.
5. **스크립트 주입**: `scripts/nexacro_automation_library.js`를 읽어 브라우저에 삽입합니다.
6. **과거 데이터 확인**:
   - `main.py`의 `is_past_data_available` 함수가 최근 2일 데이터 필요 여부를 결정합니다.
   - 내부적으로 `utils/db_util.py`의 `check_dates_exist`를 호출해 `code_outputs/db/integrated_sales.db`에 데이터가 있는지 확인합니다.
   - 없으면 먼저 과거 데이터를 수집합니다.
7. **메인 데이터 수집**:
   - `runCollectionForDate()` 함수를 호출해 오늘 데이터를 수집합니다.
   - JavaScript 로직은 Dataset에 직접 접근해 중분류 목록과 상품 목록을 추출하고, 검증 후 `window.automation.parsedData`에 저장합니다.
8. **데이터베이스 저장**:
   - Python에서 `window.automation.parsedData` 값을 읽어 `utils/db_util.py`의 `write_sales_data`로 DB에 저장합니다.
   - 이미 존재하는 상품의 경우 더 큰 판매량만 갱신합니다.
9. **판매량 예측**: `utils/db_util.py`의 `run_jumeokbap_prediction_and_save`가 내일의 주먹밥 판매량을 예측해 저장합니다.
10. **종료**: WebDriver를 종료하고 모든 과정을 마칩니다.

## 2. 주요 파일 역할

- **main.py**: 전체 과정을 지휘하는 오케스트레이터.
- **scripts/nexacro_automation_library.js**: Nexacro 환경 제어와 데이터 추출을 담당하는 핵심 스크립트.
- **utils/db_util.py**: SQLite DB 관리와 판매량 예측 로직 담당.
- **utils/log_util.py**: 로그 기록 관리.
- **config.json**: 프로젝트 설정 파일.

## 3. 데이터 흐름

```
Nexacro Dataset
      ↓ (1. JS가 추출)
임시 변수(Map)
      ↓ (2. 검증 후 전역 변수 저장)
window.automation.parsedData
      ↓ (3. Python으로 전달)
collected 변수(List[Dict])
      ↓ (4. DB 저장)
code_outputs/db/integrated_sales.db
```
