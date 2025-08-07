# BGF 자동화 프로젝트 실행 가이드 (AI 에이전트용)

## 1. 핵심 환경 (Core Environment)

이 프로젝트의 최종 실행 환경은 **Google Cloud Run 위에 배포된 도커(Docker) 컨테이너**입니다.
모든 코드는 이 환경에서 완벽하게 작동하는 것을 목표로 합니다.

## 2. 환경별 역할 (Role of Each Environment)

- **Google Cloud Shell (현재 작업 환경):**
  - **역할:** 코드 편집, Git 관리, 클라우드 명령어(`gcloud`) 실행 전용입니다.
  - **주의:** **Selenium 자동화를 이 환경에서 직접 실행하지 않습니다.** Cloud Shell은 GUI가 없는 특수한 환경이라 브라우저 실행이 매우 불안정하며, 테스트 결과가 실제 환경과 다를 수 있습니다. 여기서의 테스트는 시간 낭비일 수 있습니다.

- **도커 (Docker) / Cloud Run (실제 최종 환경):**
  - 이 프로젝트의 **실제 최종 실행 환경**입니다.
  - `Dockerfile`에 정의된 대로, 모든 필요한 프로그램과 라이브러리가 설치된 깨끗한 상태에서 코드가 실행됩니다.

## 3. 주요 파일 (Key Files)

- **`Dockerfile`**: 최종 실행 환경(도커 이미지)을 어떻게 만들지 정의하는 설계도입니다.
- **`cloudbuild.yaml`**: `Dockerfile`을 사용하여 실제 도커 이미지를 빌드하고 배포하는 과정을 자동화하는 파일입니다.
- **`main.py`**: 자동화의 모든 로직을 실행하는 메인 스크립트입니다.
- **`webdriver_utils.py`**: 웹 드라이버를 생성하는 중요한 파일. **도커 환경에서는 드라이버 경로를 직접 지정해야 합니다.**

## 4. 표준 작업 절차 (Standard Workflow)

1.  **코드 수정:** Cloud Shell에서 필요한 코드를 수정합니다.
2.  **`webdriver_utils.py` 확인:** `webdriver_utils.py` 파일의 `create_driver` 함수가 **도커 환경에 맞게** 설정되어 있는지 확인합니다. `webdriver-manager`가 아닌, **직접 경로 지정 방식**이어야 합니다.
    ```python
    # 올바른 설정 (도커용)
    service = Service("/usr/local/bin/chromedriver")
    ```
3.  **이미지 빌드 및 배포:** 다음 명령어를 사용하여 Cloud Build로 이미지를 빌드하고 Cloud Run에 배포합니다.
    ```bash
    gcloud builds submit --config cloudbuild.yaml .
    ```
4.  **테스트:** 배포된 Cloud Run 서비스를 수동으로 트리거하거나, Cloud Scheduler를 통해 실행되는 것을 확인하여 최종 테스트를 진행합니다.
