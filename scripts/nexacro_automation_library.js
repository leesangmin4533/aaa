(() => {
  // ==================================================================================
  // 1. 네임스페이스 및 기본 설정
  // ==================================================================================
  if (!window.automation) {
    window.automation = {};
  }
  Object.assign(window.automation, {
    logs: [],
    errors: [],
    error: null,
    parsedData: null,
    isCollecting: false,
  });

  window.__midCategoryLogs__ = window.__midCategoryLogs__ || [];

  // [추가] 조건이 충족될 때까지 기다리는 Promise 기반의 범용 대기 함수
  /**
   * 특정 조건이 true를 반환할 때까지 주기적으로 확인하며 기다립니다.
   * @param {function(): boolean} conditionFn - boolean을 반환하는 조건 함수
   * @param {number} [timeout=30000] - 최대 대기 시간 (ms)
   * @param {string} [timeoutMessage] - 타임아웃 시 표시할 오류 메시지
   * @returns {Promise<void>} 조건 충족 시 resolve, 타임아웃 시 reject
   */
  function waitForCondition(conditionFn, timeout = 30000, timeoutMessage = '조건 대기 시간 초과') {
    return new Promise((resolve, reject) => {
      const startTime = Date.now();
      const interval = setInterval(() => {
        if (conditionFn()) {
          clearInterval(interval);
          resolve();
        } else if (Date.now() - startTime > timeout) {
          clearInterval(interval);
          reject(new Error(timeoutMessage));
        }
      }, 250); // 250ms 마다 조건 확인
    });
  }


  // ==================================================================================
  // 2. Nexacro API 헬퍼 함수 (기존과 동일)
  // ==================================================================================

  function getNexacroApp() {
    return window.nexacro?.getApplication?.();
  }

  function getMainForm() {
    return getNexacroApp()?.mainframe?.HFrameSet00?.VFrameSet00?.FrameSet?.STMB011_M0?.form;
  }

  function selectMiddleCodeRow(rowIndex) {
    const gList = getMainForm()?.div_workForm?.form?.div2?.form?.gdList;
    if (!gList) throw new Error("gdList가 존재하지 않습니다.");
    gList.selectRow(rowIndex);
    const evt = new nexacro.GridClickEventInfo(gList, "oncellclick", false, false, false, false, 0, 0, rowIndex, rowIndex);
    gList.oncellclick._fireEvent(gList, evt);
  }


  // ==================================================================================
  // 3. 데이터 수집 함수 (기존과 동일)
  // ==================================================================================

  function collectProductsFromDataset(midCode, midName) {
    const products = [];
    const dsDetail = getMainForm()?.div_workForm?.form?.dsDetail;
    if (!dsDetail) {
      console.warn("[collectProductsFromDataset] dsDetail 데이터셋을 찾을 수 없습니다.");
      return products;
    }
    for (let i = 0; i < dsDetail.getRowCount(); i++) {
      products.push({
        midCode: midCode,
        midName: midName,
        productCode: dsDetail.getColumn(i, "ITEM_CD"),
        productName: dsDetail.getColumn(i, "ITEM_NM"),
        sales: parseInt(dsDetail.getColumn(i, "SALE_QTY") || 0, 10),
        order_cnt: parseInt(dsDetail.getColumn(i, "ORD_QTY") || 0, 10),
        purchase: parseInt(dsDetail.getColumn(i, "BUY_QTY") || 0, 10),
        disposal: parseInt(dsDetail.getColumn(i, "DISUSE_QTY") || 0, 10),
        stock: parseInt(dsDetail.getColumn(i, "STOCK_QTY") || 0, 10),
      });
    }
    console.log(`[collectProductsFromDataset] '${midName}'의 상품 ${products.length}개를 데이터셋에서 수집합니다.`);
    return products;
  }

  function getAllMidCodesFromDataset() {
    const midCodes = [];
    const dsList = getMainForm()?.div_workForm?.form?.dsList;
    if (!dsList) {
      console.warn("[getAllMidCodesFromDataset] dsList 데이터셋을 찾을 수 없습니다.");
      return midCodes;
    }
    for (let i = 0; i < dsList.getRowCount(); i++) {
      midCodes.push({
        code: dsList.getColumn(i, "MID_CD"),
        name: dsList.getColumn(i, "MID_NM"),
        expectedQuantity: parseInt(dsList.getColumn(i, "SALE_QTY") || 0, 10),
        row: i,
      });
    }
    console.log(`[getAllMidCodesFromDataset] ${midCodes.length}개의 중분류를 데이터셋에서 찾았습니다.`);
    return midCodes;
  }


  // ==================================================================================
  // 4. 메인 실행 함수 ([수정] 비동기 async/await 및 waitForCondition 적용)
  // ==================================================================================

  async function runCollectionForDate(dateStr) {
    console.log(`[DEBUG] runCollectionForDate start: ${dateStr}`);
    if (window.automation.isCollecting) {
      console.warn("이미 데이터 수집이 진행 중입니다. 새로운 요청을 무시합니다.");
      return;
    }
    window.automation.isCollecting = true;
    window.automation.error = null;
    window.automation.parsedData = null;

    try {
      // [NEW] 메인 폼(STMB011_M0)이 로드될 때까지 대기
      console.log("[runCollectionForDate] 메인 폼(STMB011_M0) 로딩 대기 중...");
      await waitForCondition(
        () => getMainForm() !== null,
        30000, // 30초 타임아웃
        "메인 폼(STMB011_M0) 로딩 시간 초과"
      );
      console.log("[runCollectionForDate] 메인 폼 로딩 완료.");

      // 날짜 설정 및 조회 버튼 클릭
      window.automation.changeDateAndSearch(dateStr);

      // [수정] 중분류 목록(dsList)이 로드될 때까지 대기
      console.log("중분류 목록 로딩 대기 중...");
      await waitForCondition(
        () => getMainForm()?.div_workForm?.form?.dsList?.getRowCount() > 0,
        30000, // 30초 타임아웃
        "중분류 목록(dsList) 로딩 시간 초과"
      );
      console.log("중분류 목록 로딩 완료.");

      const midCodesToProcess = getAllMidCodesFromDataset();
      if (midCodesToProcess.length === 0) {
        console.warn("처리할 중분류가 없습니다. 수집을 종료합니다.");
        window.automation.parsedData = [];
        window.automation.midCodesSnapshot = [];
        return;
      }
      window.automation.midCodesSnapshot = midCodesToProcess;

      const allProductsMap = new Map();

      for (const mid of midCodesToProcess) {
        console.log(`[DEBUG] 중분류 수집 시작 - ${mid.code} (${mid.name})`);

        // [수정] 중분류 클릭 후, 상세 상품 목록(dsDetail)이 로드될 때까지 대기
        // 클릭 전 상세 목록의 행 개수를 저장해두고, 클릭 후 행 개수가 바뀌기를 기다리는 방식도 가능
        selectMiddleCodeRow(mid.row);
        console.log(`'${mid.name}' 클릭. 상세 상품 목록 로딩 대기 중...`);

        await waitForCondition(
          () => getMainForm()?.div_workForm?.form?.dsDetail?.getRowCount() > 0,
          15000, // 15초 타임아웃
          `상세 상품 목록(${mid.name}) 로딩 시간 초과`
        );
        console.log("상세 상품 목록 로딩 완료.");

        const products = collectProductsFromDataset(mid.code, mid.name);

        products.forEach(p => {
          const key = `${p.midCode}_${p.productCode}`;
          if (!allProductsMap.has(key)) {
            allProductsMap.set(key, p);
          }
        });
        console.log(`[완료] 중분류: ${mid.code} (${mid.name}). 현재까지 총 ${allProductsMap.size}개 상품 수집.`);
      }

      window.automation.parsedData = Array.from(allProductsMap.values());
      console.log(`🎉 전체 수집 완료. 총 ${allProductsMap.size}개 상품, ${midCodesToProcess.length}개 중분류.`);

    } catch (e) {
      console.error("[runCollectionForDate] 데이터 수집 중 심각한 오류 발생:", e);
      window.automation.error = e.message;
    } finally {
      window.automation.isCollecting = false;
    }
  }


  // ==================================================================================
  // 5. 외부 노출 및 데이터 검증 함수 (기존과 거의 동일)
  // ==================================================================================
  window.automation.runCollectionForDate = runCollectionForDate;

  function verifyMidSaleQty(midCodeInfo) {
    if (!window.automation.parsedData) {
      console.warn("수집된 데이터가 없어 검증을 건너뜁니다.");
      return false;
    }
    const { code, name, expectedQuantity } = midCodeInfo;
    const actualQty = window.automation.parsedData
      .filter(p => p.midCode === code)
      .reduce((sum, p) => sum + p.sales, 0);

    if (expectedQuantity === actualQty) {
      console.log(`✅ [${code}] 수량 일치 → 기준 ${expectedQuantity} == 합계 ${actualQty}`);
      return true;
    } else {
      console.warn(`❌ [${code}] 수량 불일치! → 기준 ${expectedQuantity} ≠ 합계 ${actualQty}`);
      return false;
    }
  }

  function runSaleQtyVerification() {
    console.log("===== 중분류-상품 수량 합계 검증 시작 =====");
    const midCodesSnapshot = window.automation.midCodesSnapshot;
    if (!midCodesSnapshot || midCodesSnapshot.length === 0) {
      console.error("수집된 중분류 스냅샷이 없어 검증을 중단합니다.");
      return { success: false, failed_codes: ["midCodesSnapshot not found"] };
    }

    const failed_codes = midCodesSnapshot.filter(mid => !verifyMidSaleQty(mid)).map(mid => mid.code);

    console.log("===== 모든 중분류 검증 완료 =====");
    return { success: failed_codes.length === 0, failed_codes };
  }

  window.automation.runSaleQtyVerification = runSaleQtyVerification;
  console.log("Nexacro 자동화 라이브러리가 로드되었습니다.");

})();