
(() => {
  // ==================================================================================
  // 1. 네임스페이스 및 기본 설정
  // ==================================================================================
  if (!window.automation) {
    window.automation = {};
  }
  Object.assign(window.automation, {
    logs: [],
    error: null,
    parsedData: null,
    isCollecting: false,
  });

  const delay = (ms) => new Promise(res => setTimeout(res, ms));

  // 콘솔 로그 후킹
  const origConsoleLog = console.log;
  console.log = function(...args) {
    window.automation.logs.push(args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg))).join(' '));
    return origConsoleLog.apply(console, args);
  };
  const origConsoleError = console.error;
  console.error = function(...args) {
    window.automation.logs.push("[ERROR] " + args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg))).join(' '));
    return origConsoleError.apply(console, args);
  };


  // ==================================================================================
  // 2. Nexacro API 헬퍼 함수
  // ==================================================================================

  /**
   * Nexacro Application 객체를 안전하게 가져옵니다.
   * @returns {object|null} Nexacro Application 객체
   */
  function getNexacroApp() {
    if (window.nexacro && typeof window.nexacro.getApplication === 'function') {
      return window.nexacro.getApplication();
    }
    console.error("Nexacro Application을 찾을 수 없습니다.");
    return null;
  }

  /**
   * 메인 작업 폼(Form) 객체를 가져옵니다. 경로는 환경에 맞게 조정될 수 있습니다.
   * @returns {object|null} 메인 폼 객체
   */
  function getMainForm() {
    const app = getNexacroApp();
    return app?.mainframe?.HFrameSet00?.VFrameSet00?.FrameSet?.STMB011_M0?.form || null;
  }

  /**
   * ID를 사용하여 Nexacro 컴포넌트를 안전하게 찾습니다.
   * @param {string} componentId - 찾을 컴포넌트의 ID
   * @param {object} [scope=getMainForm()] - 검색을 시작할 범위 (폼 또는 컴포넌트)
   * @returns {object|null} 찾은 컴포넌트 객체
   */
  function getNexacroComponent(componentId, scope = getMainForm()) {
    if (scope && typeof scope.lookup === 'function') {
      return scope.lookup(componentId);
    }
    return null;
  }

  /**
   * 특정 트랜잭션(통신)이 완료될 때까지 기다리는 Promise를 반환합니다.
   * @param {string} svcID - 기다릴 서비스(트랜잭션)의 ID
   * @param {number} [timeout=60000] - 대기 시간 (ms)
   * @returns {Promise<void>} 트랜잭션 완료 시 resolve되는 Promise
   */
  function waitForTransaction(svcID, timeout = 60000) {
    return new Promise((resolve, reject) => {
      const form = getMainForm();
      if (!form) {
        return reject(new Error("메인 폼을 찾을 수 없어 트랜잭션을 기다릴 수 없습니다."));
      }

      const timeoutId = setTimeout(() => {
        form.fn_callback = originalCallback; // 타임아웃 시 콜백 복원
        reject(new Error(`'${svcID}' 트랜잭션 대기 시간 초과 (${timeout}ms).`));
      }, timeout);

      const originalCallback = form.fn_callback;

      form.fn_callback = function(serviceID, errorCode, errorMsg) {
        // 원래의 콜백 함수를 실행하여 기존 로직을 유지
        if (typeof originalCallback === 'function') {
          originalCallback.apply(this, arguments);
        }

        // 우리가 기다리던 서비스 ID와 일치하는지 확인
        if (serviceID === svcID) {
          clearTimeout(timeoutId);
          form.fn_callback = originalCallback; // 콜백 즉시 복원
          if (errorCode >= 0) {
            console.log(`[waitForTransaction] '${svcID}' 트랜잭션 성공적으로 완료.`);
            resolve();
          } else {
            console.error(`[waitForTransaction] '${svcID}' 트랜잭션 실패: ${errorMsg} (코드: ${errorCode})`);
            reject(new Error(`'${svcID}' 트랜잭션 실패: ${errorMsg}`));
          }
        }
      };
    });
  }


  // ==================================================================================
  // 3. 데이터 수집 함수 (Nexacro Dataset 활용)
  // ==================================================================================

  /**
   * 상품 상세 그리드(gdDetail)의 Dataset에서 모든 상품 정보를 추출합니다.
   * @param {string} midCode - 상위 중분류 코드
   * @param {string} midName - 상위 중분류 이름
   * @returns {Array<object>} 상품 데이터 객체 배열
   */
  function collectProductsFromDataset(midCode, midName) {
    const detailGrid = getNexacroComponent("gdDetail");
    if (!detailGrid) {
      console.error("상품 상세 그리드(gdDetail)를 찾을 수 없습니다.");
      return [];
    }

    const dataset = detailGrid.getBindDataset();
    if (!dataset) {
      console.error("상품 상세 그리드에 바인딩된 Dataset을 찾을 수 없습니다.");
      return [];
    }

    const products = [];
    const rowCount = dataset.getRowCount();
    console.log(`[collectProductsFromDataset] '${midName}'의 상품 ${rowCount}개를 Dataset에서 수집합니다.`);

    for (let i = 0; i < rowCount; i++) {
      products.push({
        midCode:     midCode,
        midName:     midName,
        productCode: dataset.getColumn(i, "PLU_CD") || "",
        productName: dataset.getColumn(i, "PLU_NM") || "",
        sales:       parseInt(dataset.getColumn(i, "SALE_QTY") || 0, 10),
        order_cnt:   parseInt(dataset.getColumn(i, "ORD_QTY") || 0, 10),
        purchase:    parseInt(dataset.getColumn(i, "PUR_QTY") || 0, 10),
        disposal:    parseInt(dataset.getColumn(i, "DISP_QTY") || 0, 10),
        stock:       parseInt(dataset.getColumn(i, "STOCK_QTY") || 0, 10),
      });
    }
    return products;
  }

  /**
   * 중분류 그리드(gdList)의 Dataset에서 처리해야 할 모든 중분류 목록을 추출합니다.
   * @returns {Array<object>} { code, name, expectedQuantity, row }를 포함하는 중분류 객체 배열
   */
  function getAllMidCodesFromDataset() {
    const midGrid = getNexacroComponent("gdList");
    if (!midGrid) {
      console.error("중분류 그리드(gdList)를 찾을 수 없습니다.");
      return [];
    }

    const dataset = midGrid.getBindDataset();
    if (!dataset) {
      console.error("중분류 그리드에 바인딩된 Dataset을 찾을 수 없습니다.");
      return [];
    }

    const midCodes = [];
    const rowCount = dataset.getRowCount();
    console.log(`[getAllMidCodesFromDataset] ${rowCount}개의 중분류를 Dataset에서 찾았습니다.`);

    for (let i = 0; i < rowCount; i++) {
      midCodes.push({
        code:             dataset.getColumn(i, "MID_CODE") || "",
        name:             dataset.getColumn(i, "MID_NAME") || "",
        expectedQuantity: parseInt(dataset.getColumn(i, "SALE_QTY") || 0, 10),
        row:              i,
      });
    }
    return midCodes;
  }


  // ==================================================================================
  // 4. 메인 실행 함수
  // ==================================================================================

  /**
   * 지정된 날짜의 전체 데이터 수집을 실행하는 메인 함수
   * @param {string} dateStr - 'YYYYMMDD' 형식의 날짜 문자열
   */
  async function runCollectionForDate(dateStr) {
    if (window.automation.isCollecting) {
      console.warn("이미 데이터 수집이 진행 중입니다.");
      return;
    }
    window.automation.isCollecting = true;
    window.automation.error = null;
    window.automation.parsedData = null;
    console.log(`[runCollectionForDate] ${dateStr} 데이터 수집을 시작합니다.`);

    try {
      // 1. 날짜 입력 및 메인 검색
      const dateInput = getNexacroComponent("calFromDay");
      const searchBtn = getNexacroComponent("F_10");

      if (!dateInput || !searchBtn) {
        throw new Error("날짜 입력 필드 또는 검색 버튼을 찾을 수 없습니다.");
      }

      dateInput.set_value(dateStr);
      console.log(`날짜를 '${dateStr}'로 설정했습니다.`);

      const searchTransaction = waitForTransaction("search");
      searchBtn.click();
      console.log("메인 검색 버튼을 클릭했습니다. 중분류 목록 로딩을 기다립니다...");
      await searchTransaction;
      console.log("중분류 목록 로딩 완료.");

      // 2. 처리할 중분류 목록 가져오기
      const midCodesToProcess = getAllMidCodesFromDataset();
      if (midCodesToProcess.length === 0) {
        console.warn("처리할 중분류가 없습니다. 수집을 종료합니다.");
        return;
      }
      
      const allProductsMap = new Map();
      const midGrid = getNexacroComponent("gdList");

      // 3. 각 중분류를 순회하며 상품 데이터 수집
      for (const mid of midCodesToProcess) {
        console.log(`[시작] 중분류: ${mid.code} (${mid.name})`);

        const detailTransaction = waitForTransaction("searchDetail");
        
        // Nexacro API로 특정 행을 클릭한 것과 동일한 효과를 줌
        midGrid.set_rowposition(mid.row);
        midGrid.triggerEvent("oncellclick", {
            "eventid": "oncellclick", "fromobject": midGrid, "fromreferenceobject": midGrid.getCell(mid.row, 0),
            "row": mid.row, "cell": 0,
        });
        
        console.log(`'${mid.name}'을 클릭했습니다. 상품 목록 로딩을 기다립니다...`);
        await detailTransaction;
        console.log("상품 목록 로딩 완료.");

        const products = collectProductsFromDataset(mid.code, mid.name);
        
        // 수집된 데이터를 전체 상품 맵에 병합
        products.forEach(p => {
            if (allProductsMap.has(p.productCode)) {
                const existing = allProductsMap.get(p.productCode);
                existing.sales += p.sales;
            } else {
                allProductsMap.set(p.productCode, p);
            }
        });
        console.log(`[완료] 중분류: ${mid.code} (${mid.name}). 현재까지 총 ${allProductsMap.size}개 상품 수집.`);
      }

      // 4. 최종 결과 포맷팅
      window.automation.parsedData = Array.from(allProductsMap.values());
      console.log(`🎉 전체 수집 완료. 총 ${allProductsMap.size}개 상품, ${midCodesToProcess.length}개 중분류.`);

    } catch (err) {
      console.error("데이터 수집 중 심각한 오류 발생:", err);
      window.automation.error = err.message;
    } finally {
      window.automation.isCollecting = false;
    }
  }

  // ==================================================================================
  // 5. 외부 노출
  // ==================================================================================
  window.automation.runCollectionForDate = runCollectionForDate;
  console.log("Nexacro 자동화 라이브러리가 로드되었습니다. `window.automation.runCollectionForDate('YYYYMMDD')`를 호출하여 사용하세요.");

})();
