# BGF Retail Automation

이 저장소는 BGF 리테일 시스템을 자동화하기 위한 실습용 코드 모음입니다. `analysis` 모듈에서 제공하는 함수들을 이용해 간단한 화면 전환이나 데이터 추출 작업을 수행할 수 있습니다.

다음은 중분류별 매출구성비 화면으로 이동하는 예시입니다.

```python
from selenium.webdriver.remote.webdriver import WebDriver
from analysis import navigate_to_category_mix_ratio
from utils.log_util import create_logger
import time

log = create_logger("example")

# driver는 로그인 이후의 WebDriver 인스턴스라고 가정합니다.
if navigate_to_category_mix_ratio(driver):
    log("step", "INFO", "화면 이동 성공")

    # 원하는 중분류 코드를 찾아 클릭한다.
    driver.execute_script(
        """(() => {
  const code = '201';
  const cell = [...document.querySelectorAll("div[id*='gdList.body'][id*='cell_'][id$='_0:text']")]
    .find(el => el.innerText?.trim() === code);
  if (!cell) {
    console.warn('⛔ 중분류 코드 셀 찾을 수 없음:', code);
    return false;
  }
  const clickEl = document.getElementById(cell.id.replace(':text', ''));
  const rect = clickEl.getBoundingClientRect();
  ['mousedown', 'mouseup', 'click'].forEach(type =>
    clickEl.dispatchEvent(new MouseEvent(type, {
      bubbles: true,
      cancelable: true,
      view: window,
      clientX: rect.left + rect.width / 2,
      clientY: rect.top + rect.height / 2
    }))
  );
  return true;
})();"""
        )

    # 상품 셀이 렌더링될 때까지 최대 2초간 대기한다.
    for i in range(10):
        exists = driver.execute_script(
            "return document.querySelector(\"div[id*='gdDetail.body'][id*='cell_0_0'][id$=':text']\") !== null;"
        )
        log("wait", "DEBUG", f"{i + 1}회차 로딩 상태: {exists}")
        if exists:
            log("wait", "INFO", "상품 셀이 로딩됨")
            break
        time.sleep(0.2)
    else:
        log("wait", "ERROR", "상품 셀 로딩 실패")
        raise RuntimeError("grid load failure")

    # 여기서 원하는 데이터를 직접 추출하거나 필요한 로직을 추가한다.
else:
    log("step", "ERROR", "화면 이동 실패")
```

## 로그인 설정

`login_bgf` 함수는 로그인 정보를 환경 변수 `BGF_USER_ID` 와 `BGF_PASSWORD` 에서
읽습니다. 쉘에서 다음과 같이 설정할 수 있습니다.

```bash
export BGF_USER_ID=your_id
export BGF_PASSWORD=your_password
```

윈도우를 사용한다면 PowerShell에서 다음과 같이 설정합니다.

```powershell
$env:BGF_USER_ID="your_id"
$env:BGF_PASSWORD="your_password"
```

또는 명령 프롬프트(cmd)에서는 다음과 같이 입력합니다.

```cmd
set BGF_USER_ID=your_id
set BGF_PASSWORD=your_password
```

환경 변수를 설정한 뒤 `python main.py` 를 실행하면 로그인이 진행됩니다.

환경 변수 대신 프로젝트 루트에 `.env` 파일을 생성해도 됩니다. 다음과 같이
작성하면 자동으로 값이 로드됩니다.

```env
BGF_USER_ID=1113
BGF_PASSWORD=46513
```

두 값이 제공되지 않은 경우 JSON 형식의 자격 증명 파일 경로를 `login_bgf` 의
`credential_path` 인자로 전달해야 합니다. `main.py` 에서는 환경 변수
`CREDENTIAL_FILE` 이 지정되어 있으면 해당 경로를 사용합니다.

예시 파일 구조는 다음과 같습니다.

```json
{
  "id": "YOUR_ID",
  "password": "YOUR_PASSWORD"
}
```

## main.py와 scripts 사용법

자격 증명을 준비한 뒤 아래 명령 중 하나를 실행하면 기본 자동화가 시작됩니다.

```bash
python -m aaa  # 또는 python main.py
```

`main.py` 는 Chrome 드라이버를 생성하고 `scripts/` 폴더에 존재하는 모든
JavaScript 파일을 이름순으로 실행합니다. 기본 제공 스크립트는
`click_and_extract.js` 로,
중분류를 클릭한 뒤 상품 목록을 스크롤하며 한 번에 읽어 저장합니다.
`collectAllProducts()` 함수에서 이미 수집한 상품코드는 `Set` 으로 중복을 방지합니다.
모든 작업이 끝나면 스크립트에서 `window.__parsedData__` 배열을 만들어
Python 코드가 값을 바로 읽을 수 있습니다.

실행이 끝나면 수집된 데이터가 `code_outputs/<YYYYMMDD>.txt` 파일로 저장됩니다.
각 행은 중분류 코드, 상품코드, 상품명과 매출ㆍ발주ㆍ매입ㆍ폐기ㆍ현재고 값을 탭 문자(`\t`)로 구분하여 기록합니다.
같은 날짜의 파일이 이미 존재하면 덮어쓰며, 빈 셀은 자동으로 0으로 처리됩니다.

새로운 스크립트를 `scripts/` 폴더에 추가하면 별도 수정 없이 자동으로 실행 대상에
포함됩니다.

중분류 일부만 수집하려면 예시 스크립트 `mid_range_collect.js` 를 사용할 수 있습니다.
파일 맨 아래의 `autoClickMidRange(startRow, endRow)` 호출 구간을 원하는 범위로
수정한 뒤 `main.py` 에서 해당 파일명을 지정해 실행하면 됩니다.
