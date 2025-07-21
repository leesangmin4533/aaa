# BGF Retail Automation

이 저장소는 BGF 리테일 시스템을 자동화하기 위한 실습용 코드 모음입니다. `analysis` 모듈에서 제공하는 함수들을 이용해 간단한 화면 전환이나 데이터 추출 작업을 수행할 수 있습니다.

다음은 중분류별 매출구성비 화면으로 이동하는 예시입니다.

```python
from selenium.webdriver.remote.webdriver import WebDriver
from main import run_script, wait_for_mix_ratio_page, NAVIGATION_SCRIPT
from utils.log_util import get_logger
import time

log = get_logger("example")

# 로그 파일은 매 실행 시 덮어쓰며 logs/\<YYYYMMDD\>.log 형태로 저장됩니다.

# driver는 로그인 이후의 WebDriver 인스턴스라고 가정합니다.
run_script(driver, NAVIGATION_SCRIPT)
if wait_for_mix_ratio_page(driver):
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
  const clickEl = document.getElementById(cell.id.split(':text')[0]);
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

`main.py` 는 Chrome 드라이버로 로그인한 뒤
"중분류별 매출 구성비" 화면에 진입하면 `scripts/auto_collect_mid_products.js`
와 `scripts/data_collect_listener.js` 두 스크립트를 순서대로 실행합니다.
첫 스크립트는 중분류와 상품코드를 자동으로 클릭하며, 클릭 시마다 커스텀 이벤트를 발생시킵니다.
두 번째 스크립트는 이 이벤트를 감지해 오른쪽 그리드의 텍스트를 모아 `window.__liveData__` 배열에 누적합니다.

`main.py` 는 주기적으로 이 배열을 읽어 `code_outputs/<YYYYMMDD>.txt` 파일에 추가합니다.
같은 날짜의 파일이 이미 존재하면 처음 시작 시 한 번만 삭제 후 새로 생성하며,
이후에는 이벤트가 발생할 때마다 중복되지 않는 새 라인만 이어서 기록합니다.

각 줄은 다음 순서의 필드가 탭 문자로 구분되어 저장됩니다.

```
midCode    midName    productCode    productName    sales    order    purchase    discard    stock
```

현재는 `scripts/auto_collect_mid_products.js` 가 결과 파일 저장까지 자동으로 처리합니다.
따라서 예전에 사용하던 `download_with_blob.js` 는 더 이상 필요하지 않습니다.

## 데이터가 수집되지 않을 때

수집 스크립트 실행 후 `window.__parsedData__` 값이 비어 있다면
브라우저 콘솔 로그를 확인해 보세요. `main.py`는 데이터가 없을 경우
`driver.get_log("browser")` 결과와 `window.__parsedDataError__` 값을 출력하므로
오류 메시지를 통해 문제 원인을 파악할 수 있습니다.

## SQLite 기반 자동 저장

`main.py`를 실행하면 현재 날짜를 기준으로 `code_outputs/`\`YYYYMMDD.db\` 파일이
자동 생성됩니다. 하루 동안 해당 파일을 계속 사용하며, 각 행의 `collected_at` 필드는
"YYYY-MM-DD HH:MM" 형식으로 기록됩니다.

DB에는 `mid_sales` 테이블이 존재하며 대략 다음과 같이 구성됩니다.

```
id INTEGER PRIMARY KEY AUTOINCREMENT
collected_at TEXT
mid_code TEXT
mid_name TEXT
product_code TEXT
product_name TEXT
sales INTEGER
order_cnt INTEGER
purchase INTEGER
disposal INTEGER
stock INTEGER
```

### 1시간 단위 실행 예시

- **Windows 작업 스케줄러**
  1. 새 작업을 만들고 트리거를 "매 1시간"으로 지정합니다.
  2. 동작에 파이썬 실행 파일과 `main.py` 경로를 입력하면 됩니다.
- **서버(cron)**
  `crontab -e`로 편집하여 다음 줄을 추가하면 정각마다 실행됩니다.

  ```cron
  0 * * * * /usr/bin/python /경로/main.py
  ```

## JavaScript 자동 클릭 예시

아래 코드는 중분류 코드와 상품코드를 순회하며 차례대로 클릭하는 간단한 스크립트입니다. 실행 후에는 수집된 결과를 `code_outputs/<YYYYMMDD>.txt` 파일에 저장하며, 같은 날짜의 파일이 이미 존재하면 덮어씁니다. 한 번의 실행 과정에서 만들어진 로그는 모두 누적하여 기록됩니다.

```javascript
(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  async function clickElementById(id) {
    const el = document.getElementById(id);
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    ["mousedown", "mouseup", "click"].forEach(type =>
      el.dispatchEvent(new MouseEvent(type, {
        bubbles: true,
        cancelable: true,
        view: window,
        clientX: rect.left + rect.width / 2,
        clientY: rect.top + rect.height / 2
      }))
    );
    return true;
  }

  async function autoClickAllProductCodes() {
    const seen = new Set();
    let scrollCount = 0;

    while (true) {
      const textCells = [...document.querySelectorAll("div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']")];
      const newCodes = [];

      for (const textEl of textCells) {
        const code = textEl.innerText?.trim();
        if (!/^\d{13}$/.test(code)) continue;
        if (seen.has(code)) continue;

        const clickId = textEl.id.replace(":text", "");
        const clicked = await clickElementById(clickId);
        if (!clicked) {
          console.warn("❌ 상품 클릭 대상 없음 → ID:", clickId);
          continue;
        }

        seen.add(code);
        newCodes.push(code);
        console.log(`✅ 상품 클릭 완료: ${code}`);
        await delay(300);
      }

      if (newCodes.length === 0) break;

      const scrollBtn = document.querySelector("div[id$='gdDetail.vscrollbar.incbutton:icontext']");
      if (!scrollBtn) break;

      await clickElementById(scrollBtn.id);
      scrollCount++;
      console.log(`🔄 상품 스크롤 ${scrollCount}회`);
      await delay(1000);
    }

    console.log("🎉 상품코드 클릭 완료");
  }

  async function autoClickAllMidCodesAndProducts() {
    const seenMid = new Set();
    let scrollCount = 0;

    while (true) {
      const textCells = [...document.querySelectorAll("div[id*='gdList.body'][id*='cell_'][id$='_0:text']")];
      const newMids = [];

      for (const textEl of textCells) {
        const code = textEl.innerText?.trim();
        if (!/^\d{3}$/.test(code)) continue;
        if (seenMid.has(code)) continue;

        const clickId = textEl.id.replace(":text", "");
        const clicked = await clickElementById(clickId);
        if (!clicked) {
          console.warn("❌ 중분류 클릭 대상 없음 → ID:", clickId);
          continue;
        }

        seenMid.add(code);
        newMids.push(code);
        console.log(`✅ 중분류 클릭 완료: ${code}`);
        await delay(500);  // 중분류 클릭 후 화면 렌더링 대기

        await autoClickAllProductCodes(); // 상품코드 클릭 루프 진입
        await delay(300); // 다음 중분류 넘어가기 전 딜레이
      }

      if (newMids.length === 0) break;

      const scrollBtn = document.querySelector("div[id$='gdList.vscrollbar.incbutton:icontext']");
      if (!scrollBtn) break;

      await clickElementById(scrollBtn.id);
      scrollCount++;
      console.log(`🔄 중분류 스크롤 ${scrollCount}회`);
      await delay(1000);
    }

    console.log("🎉 전체 작업 완료: 중분류 수", seenMid.size);
  }

  autoClickAllMidCodesAndProducts(); // 🔰 Entry Point
})();
```
