# BGF 자동화 프로젝트: 주요 흐름 및 아키텍처

이 문서는 BGF 자동화 프로젝트의 전반적인 데이터 수집 및 처리 흐름을 설명합니다.

## 1. 실행 순서

1. **시작**: 사용자가 `python main.py`를 실행하면 `config.json`에 정의된 모든 점포에 대해 순차적으로 처리가 이루어집니다.
2. **점포별 처리 흐름**:
   1. **로그 초기화**: `utils/log_util.py`가 `logs/automation.log` 파일을 매 실행 시 새로 만듭니다.
   2. **드라이버 생성**: Selenium WebDriver 인스턴스를 생성합니다.
   3. **로그인 및 팝업 처리**: `login/login_bgf.py`로 로그인 후 `utils/popup_util.py`로 팝업을 닫습니다.
   4. **스크립트 주입**: `nexacro_automation_library.js`, `date_changer.js`, `navigation.js`를 차례로 실행합니다.
   5. **과거 데이터 확인**: `utils/db_util.py`의 `get_missing_past_dates`로 점포별 DB에서 최근 7일 중 누락된 날짜를 찾습니다.
   6. **과거 데이터 수집**: 누락된 날짜가 있다면 `runCollectionForDate()`를 호출하여 데이터를 수집하고 DB에 저장합니다.
   7. **오늘 데이터 수집**: 현재 날짜의 데이터를 수집해 DB에 저장합니다.
   8. **판매량 예측**: `utils/db_util.py`의 `run_all_category_predictions`로 중분류별 판매량을 예측하고 추천 상품 조합을 기록합니다.
   9. **종료**: WebDriver를 종료하고 다음 점포로 이동합니다.

## 2. 주요 파일 역할

- **main.py**: 모든 점포에 대한 데이터 수집과 예측 과정을 지휘합니다.
- **scripts/nexacro_automation_library.js**: Nexacro 환경 제어와 데이터 추출을 담당하는 핵심 스크립트.
- **utils/db_util.py**: SQLite DB 관리, 과거 데이터 확인, 판매량 예측 및 추천 조합 생성 로직 담당.
- **utils/log_util.py**: 로그 기록 관리.
- **config.json**: 프로젝트 설정 파일.
- **scheduler/scheduler.py**: 매 시간 정각에 자동화를 실행하는 스케줄러 스크립트.

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
code_outputs/db/<store>.db
```
