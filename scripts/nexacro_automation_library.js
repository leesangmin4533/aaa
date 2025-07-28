(() => {
  try {
  // ==================================================================================
  // 1. 네임스페이스 및 기본 설정
  // ==================================================================================
  // window.automation 객체가 없으면 초기화하고, 필요한 속성들을 할당합니다.
  if (!window.automation) {
    window.automation = {};
  }
  Object.assign(window.automation, {
    logs: [],         // 자동화 과정에서 발생하는 모든 로그를 저장
    errors: [],       // 자동화 과정에서 발생하는 오류 로그만 별도 저장
    error: null,      // 최종적으로 발생한 오류 메시지 저장
    parsedData: null, // 최종적으로 파싱된 데이터를 저장
    isCollecting: false, // 현재 데이터 수집이 진행 중인지 여부
  });

  // 중분류 클릭 과정을 별도로 추적하기 위한 로그 배열
  window.__midCategoryLogs__ = window.__midCategoryLogs__ || [];

  // 비동기 작업을 위한 딜레이 함수
  const delay = (ms) => new Promise(res => setTimeout(res, ms));

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

  

  // 콘솔 로그를 후킹하여 window.automation.logs에 저장
  const origConsoleLog = console.log;
  console.log = function(...args) {
    window.automation.logs.push(args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg))).join(' '));
    return origConsoleLog.apply(console, args);
  };
  // 콘솔 에러를 후킹하여 window.automation.logs 및 window.automation.errors에 저장
  const origConsoleError = console.error;
  console.error = function(...args) {
    const errorMsg = "[ERROR] " + args.map(arg => {
      if (arg instanceof Error) {
        return arg.message; // Extract message from Error objects
      }
      return (typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg));
    }).join(' ');
    window.automation.logs.push(errorMsg);
    window.automation.errors.push(errorMsg);
    return origConsoleError.apply(console, args);
  };


  // ==================================================================================
  // 2. Nexacro API 헬퍼 함수
  //    (넥사크로 내부 컴포넌트 및 트랜잭션에 안정적으로 접근하기 위한 함수들)
  // ==================================================================================

  /**
   * Nexacro Application 객체를 안전하게 가져옵니다.
   * @returns {object|null} Nexacro Application 객체 또는 null
   */
  function getNexacroApp() {
    const app = window.nexacro && typeof window.nexacro.getApplication === 'function' ? window.nexacro.getApplication() : null;
    if (app) {
      console.log("[getNexacroApp] Nexacro Application 객체를 찾았습니다.");
    } else {
      console.warn("[getNexacroApp] Nexacro Application 객체를 찾을 수 없습니다.");
    }
    return app;
  }

  /**
   * 메인 작업 폼(Form) 객체를 가져옵니다.
   * 이 경로는 넥사크로 애플리케이션의 실제 구조에 따라 조정될 수 있습니다.
   * 현재는 '매출분석 > 중분류별 매출 구성비' 화면의 폼 경로를 가정합니다.
   * @returns {object|null} 메인 폼 객체 또는 null
   */
  function getMainForm() {
    const app = getNexacroApp();
    // TODO: 이 경로는 실제 넥사크로 애플리케이션의 메인 폼 경로에 맞게 수정해야 합니다.
    const mainForm = app?.mainframe?.HFrameSet00?.VFrameSet00?.FrameSet?.STMB011_M0?.form || null;
    if (mainForm) {
      console.log("[getMainForm] 메인 폼(STMB011_M0)을 찾았습니다.");
    } else {
      console.warn("[getMainForm] 메인 폼(STMB011_M0)을 찾을 수 없습니다. 경로 확인 필요.");
    }
    return mainForm;
  }

  /**
   * ID를 사용하여 Nexacro 컴포넌트를 안전하게 찾습니다.
   * Nexacro의 `lookup` 메서드를 사용하여 컴포넌트 계층 구조를 탐색합니다.
   * @param {string} componentId - 찾을 컴포넌트의 ID (예: "gdList", "calFromDay")
   * @param {object} [initialScope=null] - 검색을 시작할 초기 범위 (폼 또는 컴포넌트). 지정하지 않으면 getMainForm()을 기다림.
   * @param {number} [timeout=15000] - 컴포넌트를 기다릴 최대 시간 (ms)
   * @returns {Promise<object|null>} 찾은 컴포넌트 객체 또는 null (타임아웃 시)
   */
  async function getNexacroComponent(componentId, initialScope = null, timeout = 10000) {
    console.log(`[getNexacroComponent] 컴포넌트 대기 중: "${componentId}" (시간 초과: ${timeout}ms)`);
    const start = Date.now();
    let currentScope = initialScope;

    while (Date.now() - start < timeout) {
      if (!currentScope) {
        // 초기 스코프가 지정되지 않았으면 메인 폼이 준비될 때까지 기다림
        currentScope = getMainForm();
        if (!currentScope) {
          await delay(500); // 메인 폼이 나타날 때까지 대기
          continue;
        }
      }

      if (currentScope && typeof currentScope.lookup === 'function') {
        const component = currentScope.lookup(componentId); // Nexacro의 lookup 메서드 사용
        if (component) {
          console.log(`[getNexacroComponent] 성공! 컴포넌트 찾음: "${componentId}"`);
          return component;
        }
      } else {
        console.warn(`[getNexacroComponent] 현재 스코프가 유효하지 않거나 lookup 함수가 없습니다. 컴포넌트: "${componentId}"`);
      }
      await delay(500); // 0.5초마다 재시도하여 대기 시간 단축
    }
    console.error(`[getNexacroComponent] 시간 초과! 컴포넌트를 찾을 수 없습니다: "${componentId}"`);
    return null; // 타임아웃 시 null 반환
  }

  /**
   * 특정 넥사크로 트랜잭션(통신)이 완료될 때까지 기다리는 Promise를 반환합니다.
   * 넥사크로 폼의 fn_callback 함수를 후킹하여 트랜잭션 완료를 감지합니다.
   * @param {string} svcID - 기다릴 서비스(트랜잭션)의 ID (예: "search", "searchDetail")
   * @param {number} [timeout=120000] - 대기 시간 (ms)
   * @returns {Promise<void>} 트랜잭션 완료 시 resolve되는 Promise
   */
  function waitForTransaction(svcID, timeout = 15000) {
    console.log(`[waitForTransaction] 서비스 ID 대기 중: '${svcID}' (시간 초과: ${timeout}ms)`);
    return new Promise((resolve, reject) => {
      const form = getMainForm();
      if (!form) {
        return reject(new Error("메인 폼을 찾을 수 없어 트랜잭션을 기다릴 수 없습니다."));
      }

      let originalCallback = form.fn_callback; // 기존 콜백 함수 백업
      let callbackRestored = false; // 콜백 복원 여부 플래그

      const restoreCallback = () => {
        if (!callbackRestored) {
          form.fn_callback = originalCallback; // 원래 콜백 복원
          callbackRestored = true;
        }
      };

      const timeoutId = setTimeout(() => {
        restoreCallback(); // 타임아웃 시 원래 콜백 복원
        console.error(`[waitForTransaction] 시간 초과! 서비스 ID '${svcID}'가 ${timeout}ms 후 타임아웃되었습니다.`);
        reject(new Error(`'${svcID}' 트랜잭션 대기 시간 초과 (${timeout}ms).`));
      }, timeout);

      // 넥사크로 폼의 fn_callback 함수를 오버라이드
      form.fn_callback = function(serviceID, errorCode, errorMsg) {
        // 원래의 콜백 함수를 먼저 실행하여 기존 로직을 유지
        if (typeof originalCallback === 'function') {
          originalCallback.apply(this, arguments);
        }

        const baseServiceID = serviceID.split('|')[0]; // 실제 서비스 ID는 '|'의 첫 부분
        console.log(`[waitForTransaction] fn_callback 호출됨: 수신 서비스 ID='${serviceID}', 기본 ID='${baseServiceID}', 기대 ID='${svcID}'`);

        // 우리가 기다리던 서비스 ID와 일치하는지 확인
        if (baseServiceID === svcID) {
          clearTimeout(timeoutId); // 타임아웃 타이머 해제
          if (errorCode >= 0) { // 에러 코드가 0 이상이면 성공으로 간주
            console.log(`[waitForTransaction] '${svcID}' 트랜잭션 성공적으로 완료. Promise 해결.`);
            resolve();
          } else {
            console.error(`[waitForTransaction] '${svcID}' 트랜잭션 실패: ${errorMsg} (코드: ${errorCode})`);
            reject(new Error(`'${svcID}' 트랜잭션 실패: ${errorMsg}`));
          }
          restoreCallback(); // 콜백 함수 복원
        } else {
          console.log(`[waitForTransaction] 다른 트랜잭션 완료: 수신 서비스 ID='${serviceID}'. 여전히 '${svcID}' 대기 중.`);
        }
      };
    });
  }

  function selectMiddleCodeRow(rowIndex) {
    const f = getMainForm();
    const gList = f?.div_workForm?.form?.div2?.form?.gdList;
    if (!gList) throw new Error("gdList가 존재하지 않습니다.");

    // 실제 클릭은 여기서 한 번만 발생합니다.
    gList.selectRow(rowIndex);
    const evt = new nexacro.GridClickEventInfo(gList, "oncellclick", false, false, false, false, 0, 0, rowIndex, rowIndex);
    gList.oncellclick._fireEvent(gList, evt);
  }


  // 호출 전에 mainForm 생성 대기
  const ensureMainFormLoaded = async () => {
    for (let i = 0; i < 50; i++) {
      const form = getMainForm();
      if (form) return true;
    await delay(500);
    }
    throw new Error("mainForm이 15초 내 생성되지 않았습니다.");
  };


  // ==================================================================================
  // 3. 데이터 수집 함수 (Nexacro Dataset 활용)
  //    (DOM 파싱 대신 넥사크로 Dataset API를 사용하여 데이터 수집)
  // ==================================================================================

  /**
   * 상품 상세 그리드(gdDetail)에 바인딩된 Dataset에서 모든 상품 정보를 추출합니다.
   * 이 방식은 DOM 구조에 의존하지 않고 넥사크로 내부 데이터 모델에서 직접 데이터를 가져오므로 매우 안정적입니다.
   * @param {string} midCode - 상위 중분류 코드
   * @param {string} midName - 상위 중분류 이름
   * @returns {Array<object>} 상품 데이터 객체 배열
   */
  async function collectProductsFromDataset(midCode, midName, scope) {
    const products = [];
    const dsDetail = getMainForm()?.div_workForm?.form?.dsDetail; // 넥사크로 데이터셋 객체 직접 접근

    if (!dsDetail) {
      console.warn("[collectProductsFromDataset] dsDetail 데이터셋을 찾을 수 없습니다.");
      return products;
    }

    for (let i = 0; i < dsDetail.getRowCount(); i++) {
      products.push({
        midCode:     midCode,
        midName:     midName,
        productCode: dsDetail.getColumn(i, "ITEM_CD"),
        productName: dsDetail.getColumn(i, "ITEM_NM"),
        sales:       parseInt(dsDetail.getColumn(i, "SALE_QTY") || 0, 10),
        order_cnt:   parseInt(dsDetail.getColumn(i, "ORD_QTY") || 0, 10),
        purchase:    parseInt(dsDetail.getColumn(i, "BUY_QTY") || 0, 10),
        disposal:    parseInt(dsDetail.getColumn(i, "DISUSE_QTY") || 0, 10),
        stock:       parseInt(dsDetail.getColumn(i, "STOCK_QTY") || 0, 10),
      });
    }
    console.log(`[collectProductsFromDataset] '${midName}'의 상품 ${products.length}개를 데이터셋에서 수집합니다.`);
    return products;
  }

  async function getAllMidCodesFromDataset(scope) {
    const midCodes = [];
    const dsList = getMainForm()?.div_workForm?.form?.dsList; // 넥사크로 데이터셋 객체 직접 접근

    if (!dsList) {
      console.warn("[getAllMidCodesFromDataset] dsList 데이터셋을 찾을 수 없습니다.");
      return midCodes;
    }

    for (let i = 0; i < dsList.getRowCount(); i++) {
      const code = dsList.getColumn(i, "MID_CD");
      const name = dsList.getColumn(i, "MID_NM");

      midCodes.push({
        code:             code,
        name:             name,
        expectedQuantity: parseInt(dsList.getColumn(i, "SALE_QTY") || 0, 10), // 데이터셋에서 직접 기대수량 가져옴
        row:              i, // 데이터셋 행 인덱스
      });
    }
    console.log(`[getAllMidCodesFromDataset] ${midCodes.length}개의 중분류를 데이터셋에서 찾았습니다.`);
    return midCodes;
  }


  // ==================================================================================
  // 4. 메인 실행 함수
  //    (특정 날짜에 대한 전체 데이터 수집 흐름 제어)
  // ==================================================================================

  /**
   * 지정된 날짜의 전체 데이터 수집을 실행하는 메인 함수입니다.
   * 이 함수는 날짜 설정, 메인 검색, 중분류 순회, 상품 데이터 수집의 전 과정을 제어합니다.
   * @param {string} dateStr - 'YYYYMMDD' 형식의 날짜 문자열
   */
  async function runCollectionForDate(dateStr) {
    if (window.automation.isCollecting) {
      console.warn("이미 데이터 수집이 진행 중입니다. 새로운 요청을 무시합니다.");
      return;
    }
    window.automation.isCollecting = true; // 수집 시작 플래그 설정
    window.automation.error = null; // 이전 오류 초기화
    window.automation.errors = []; // 이전 오류 로그 초기화
    window.automation.parsedData = null; // 이전 데이터 초기화
    console.log(`[runCollectionForDate] ${dateStr} 데이터 수집을 시작합니다.`);

    try {
      // 1. 메인 폼 로딩 확인
      await ensureMainFormLoaded();

      // 2. 메인 폼 및 필수 컴포넌트(날짜 입력 필드, 검색 버튼) 찾기
      const mainForm = getMainForm();
      if (!mainForm) {
        throw new Error("메인 폼(STMB011_M0)을 찾을 수 없습니다. 자동화를 시작할 수 없습니다.");
      }

      // 날짜 입력 필드 컴포넌트 (calFromDay) 찾기
      console.log("[runCollectionForDate] 날짜 입력 필드(calFromDay) 컴포넌트 탐색 시작...");
      const calFromDay = await getNexacroComponent("calFromDay", mainForm); // mainForm을 scope로 사용
      if (!calFromDay) {
        throw new Error("날짜 입력 필드 'calFromDay' 컴포넌트를 찾을 수 없습니다. getNexacroComponent가 null을 반환했습니다.");
      }
      if (!calFromDay.calendaredit) {
        throw new Error("날짜 입력 필드 'calFromDay' 컴포넌트에는 'calendaredit' 속성이 없습니다. 경로 확인 필요.");
      }
      const dateInput = calFromDay.calendaredit;
      console.log("[runCollectionForDate] 날짜 입력 필드(calFromDay) 컴포넌트 찾기 성공.");

      // 검색 버튼 컴포넌트 (F_10) 찾기
      console.log("[runCollectionForDate] 검색 버튼(F_10) 컴포넌트 탐색 시작...");
      const searchBtn = await getNexacroComponent("F_10", mainForm); // mainForm을 scope로 사용
      if (!searchBtn) {
        throw new Error("검색 버튼(F_10)을 찾을 수 없습니다. 경로 확인 필요.");
      }
      console.log("[runCollectionForDate] 검색 버튼(F_10) 컴포넌트 찾기 성공.");

      // 2. 날짜 설정 및 메인 검색 버튼 클릭 (트랜잭션 강제 재발행)
      // 날짜를 초기화했다가 다시 설정하여, 앱이 변경을 인지하고 새 트랜잭션을 보내도록 함
      dateInput.set_value("");
      await delay(500); // UI 반영 대기 시간을 0.5초로 단축
      dateInput.set_value(dateStr);
      console.log(`날짜를 '${dateStr}'로 설정했습니다.`);

      // 넥사크로 컴포넌트의 .click() 메서드를 사용하여 클릭 이벤트 트리거
      searchBtn.click();
      console.log("메인 검색 버튼을 클릭했습니다. 중분류 목록 로딩을 기다립니다...");
      
      // 중분류 목록(gdList)이 로드될 때까지 대기
      await new Promise((resolve, reject) => {
        const checkInterval = setInterval(() => {
          const firstMidCodeCell = document.querySelector("div[id*='gdList.body'][id*='cell_0_0:text']");
          if (firstMidCodeCell && firstMidCodeCell.innerText.trim().length > 0) {
            clearInterval(checkInterval);
            resolve();
          }
        }, 500); // 0.5초마다 확인
        setTimeout(() => {
          clearInterval(checkInterval);
          reject(new Error("중분류 목록 로딩 시간 초과."));
        }, 120000); // 120초 타임아웃
      });
      console.log("중분류 목록 로딩 완료.");
      await delay(700); // DOM 렌더링을 위한 추가 대기

      // 3. 모든 중분류 항목이 로드되도록 스크롤 및 클릭 (이 단계는 더 이상 필요하지 않습니다.)
      // await autoClickAllMidCodes();

      // 4. 처리할 중분류 목록 가져오기 (Dataset에서 직접 가져옴)
      const midCodesToProcess = await getAllMidCodesFromDataset(mainForm.div_workForm.form.div2.form);
      if (midCodesToProcess.length === 0) {
        console.warn("처리할 중분류가 없습니다. 수집을 종료합니다.");
        window.automation.parsedData = []; // 데이터가 없는 경우 빈 배열로 설정
        window.automation.midCodesSnapshot = []; // 스냅샷도 비워줍니다.
        return;
      }
      window.automation.midCodesSnapshot = midCodesToProcess; // 중분류 스냅샷 저장
      
      const allProductsMap = new Map(); // 전체 상품 데이터를 저장할 Map (중복 방지 및 합산)

      // 4. 각 중분류를 순회하며 상품 데이터 수집
      for (const mid of midCodesToProcess) {
        console.log(`
[시작] 중분류: ${mid.code} (${mid.name})`);

        selectMiddleCodeRow(mid.row);
        
        console.log(`'${mid.name}'을 클릭했습니다. 상품 목록 로딩을 기다립니다...`);
        // 트랜잭션 완료 대기 (DOM 기반 대기로 변경)
        await new Promise((resolve, reject) => {
          const checkInterval = setInterval(() => {
            const firstProductCodeCell = document.querySelector("div[id*='gdDetail.body'][id*='cell_0_0:text']");
            if (firstProductCodeCell && firstProductCodeCell.innerText.trim().length > 0) {
              clearInterval(checkInterval);
              resolve();
            }
          }, 500); // 0.5초마다 확인
          setTimeout(() => {
            clearInterval(checkInterval);
            reject(new Error("상품 목록 로딩 시간 초과."));
          }, 120000); // 120초 타임아웃
        });
        console.log("상품 목록 로딩 완료.");
        await delay(500); // 추가 대기 (0.5초)
        await delay(700); // DOM 렌더링을 위한 추가 대기
        console.log("상품 목록 로딩 완료.");

        // 상품 상세 그리드의 Dataset에서 상품 데이터 수집
        const products = await collectProductsFromDataset(mid.code, mid.name, mainForm.div_workForm.form.div2.form);
        
        // 수집된 상품 데이터를 전체 상품 맵에 병합 (중복 방지 및 합산)
        products.forEach(p => {
            const key = `${p.midCode}_${p.productCode}`;
            if (allProductsMap.has(key)) {
                const existing = allProductsMap.get(key);
                console.warn(`[merge] duplicate product ${p.productCode} existing-mid=${existing.midCode} new-mid=${p.midCode}`);
                existing.sales += p.sales;
                existing.order_cnt += p.order_cnt;
                existing.purchase += p.purchase;
                existing.disposal += p.disposal;
                existing.stock += p.stock;
            } else {
                allProductsMap.set(key, p); // 새로운 상품이면 그대로 추가
            }
        });
        console.log(`[완료] 중분류: ${mid.code} (${mid.name}). 현재까지 총 ${allProductsMap.size}개 상품 수집.`);
      }

      // Map의 값을 배열로 변환하여 window.automation.parsedData에 저장
      window.automation.parsedData = Array.from(allProductsMap.values());

      // 5. 최종 검증 및 결과 포맷팅
      const verification = await runSaleQtyVerification();
      console.log(`[runCollectionForDate] verification result: ${JSON.stringify(verification)}`);
      console.log(`🎉 전체 수집 완료. 총 ${allProductsMap.size}개 상품, ${midCodesToProcess.length}개 중분류.`);

    } catch (err) {
      console.error("데이터 수집 중 심각한 오류 발생:", err.message || err); // 오류 메시지 상세화
      window.automation.error = err.message; // 오류 메시지 저장
    } finally {
      window.automation.isCollecting = false; // 수집 종료 플래그 설정
    }
  }

  // ==================================================================================
  // 5. 외부 노출 (파이썬 Selenium에서 호출할 함수)
  // ==================================================================================
  // 이 함수를 window.automation 객체에 노출하여 파이썬 스크립트에서 driver.execute_script()로 호출할 수 있게 합니다.
  window.automation.runCollectionForDate = runCollectionForDate;
  
  // ==================================================================================
  // 6. 데이터 검증 함수
  // ==================================================================================

  /**
   * 특정 중분류의 SALE_QTY와 그에 속한 상품들의 SALE_QTY 총합이 일치하는지 검증합니다.
   * @param {number} rowIndex - 검증할 중분류의 dsList 내 행 인덱스
   * @returns {Promise<boolean>} 검증 성공 시 true, 실패 시 false 반환
   */
  async function verifyMidSaleQty(midCodeInfo) {
    try {
      if (!window.automation.parsedData) { // parsedData가 없으면 검증 불가
        console.warn("수집된 데이터(window.automation.parsedData)가 없습니다. 검증을 건너뜁니다.");
        return false;
      }

      const midCode = midCodeInfo.code;
      const midName = midCodeInfo.name;
      const expectedQty = midCodeInfo.expectedQuantity;

      console.log(`▶ 중분류 [${midCode} - ${midName}] 검증 시작, 기준 수량: ${expectedQty}`);

      // 수집된 데이터(window.automation.parsedData)에서 해당 중분류의 상품 수량 합계를 계산합니다.
      let actualQty = 0;
      const productsForMidCode = window.automation.parsedData.filter(p => p.midCode === midCode);
      for (const p of productsForMidCode) {
        actualQty += p.sales; // 'sales' 필드를 합산
      }

      if (expectedQty === actualQty) {
        console.log(`✅ [${midCode}] 수량 일치 → 기준 ${expectedQty} == 합계 ${actualQty}`);
        return true;
      } else {
        console.warn(`❌ [${midCode}] 수량 불일치! → 기준 ${expectedQty} ≠ 합계 ${actualQty}`);
        return false;
      }
    } catch (e) {
      console.error(`[verifyMidSaleQty] 검증 중 오류 발생 (midCode: ${midCodeInfo?.code || 'N/A'}):`, e.message);
      return false;
    }
  }

  /**
   * 모든 중분류에 대해 수량 검증을 실행하고, 최종 결과를 객체로 반환합니다.
   * @returns {Promise<object>} { success: boolean, failed_codes: Array<string> }
   */
  async function runSaleQtyVerification() {
      console.log("===== 중분류-상품 수량 합계 검증 시작 =====");
      const midCodesSnapshot = window.automation.midCodesSnapshot;
      if (!midCodesSnapshot || midCodesSnapshot.length === 0) {
          console.error("수집된 중분류 스냅샷 데이터(window.automation.midCodesSnapshot)가 없습니다. 검증을 중단합니다.");
          return { success: false, failed_codes: ["midCodesSnapshot not found"] };
      }

      const failed_codes = [];
      for (const midCodeInfo of midCodesSnapshot) {
          const isSuccess = await verifyMidSaleQty(midCodeInfo);
          if (!isSuccess) {
              failed_codes.push(midCodeInfo.code);
          }
          // 검증은 라이브 데이터에 영향을 주지 않으므로 delay는 필요 없습니다.
      }

      console.log("===== 모든 중분류 검증 완료 =====");
      if (failed_codes.length > 0) {
          return { success: false, failed_codes: failed_codes };
      } else {
          return { success: true, failed_codes: [] };
      }
  }

  window.automation.runSaleQtyVerification = runSaleQtyVerification; // 검증 함수 노출

  console.log("Nexacro 자동화 라이브러리가 로드되었습니다. `runCollectionForDate('YYYYMMDD')` 또는 `runSaleQtyVerification()`를 호출하여 사용하세요.");

  } catch (e) {
    // 라이브러리 로드 및 초기화 시점에 발생하는 오류를 잡습니다.
    if (window.automation) {
      window.automation.error = "라이브러리 초기화 오류: " + e.message;
      window.automation.errors.push("라이브러리 초기화 오류: " + e.message);
      window.automation.logs.push("[FATAL ERROR] 라이브러리 초기화 오류: " + e.message);
    } else {
      // window.automation 객체조차 초기화되지 않은 경우 (매우 드물지만)
      console.error("FATAL ERROR: window.automation 객체 초기화 전 라이브러리 로드 오류 발생: ", e);
    }
  }
})();