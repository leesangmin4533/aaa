(() => {
  // 1. 네임스페이스 및 유틸리티 설정
  window.automation = {
    logs: [],
    parsedData: null,
    error: null,
    verificationResults: [], // 새로운 검증 결과 저장 배열
  };

  const delay = (ms) => new Promise((res) => setTimeout(res, ms));

  async function clickElementById(id) {
    const el = document.getElementById(id);
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    ["mousedown", "mouseup", "click"].forEach((type) =>
      el.dispatchEvent(
        new MouseEvent(type, {
          bubbles: true,
          cancelable: true,
          view: window,
          clientX: rect.left + rect.width / 2,
          clientY: rect.top + rect.height / 2,
        })
      )
    );
    return true;
  }

  function getText(row, col, grid = "gdDetail") {
    const el = document.querySelector(
      `div[id*='${grid}.body'][id*='cell_${row}_${col}'][id$=':text']`
    );
    return el?.innerText?.trim() || "";
  }

  // 2. 상품 데이터 수집 함수 (대기 시간 최적화 및 전체 상품 코드 중복 방지)
  async function collectProductDataForMid(midCode, midName, expectedQuantity) {
    console.log(`[START] 상품 수집: ${midCode} (${midName}), 기대수량: ${expectedQuantity}`);
    document.dispatchEvent(new CustomEvent("mid-clicked", { detail: { code: midCode, midName } }));

    const gridBody = await (async () => {
        for (let i = 0; i < 10; i++) {
            const el = document.querySelector("div[id*='gdDetail.body']");
            if (el) return el;
            await delay(300);
        }
        throw new Error("상품 그리드 body를 찾을 수 없습니다.");
    })();

    const productDataForMid = []; // 현재 중분류에서 수집된 상품 데이터 (객체 형태)
    const seenCodesInMid = new Set(); // 현재 중분류 내에서만 본 상품 코드
    let actualQuantity = 0;
    let noChangeScrolls = 0;

    while (noChangeScrolls < 3) {
      let newProductsFoundInView = false;

      const rowEls = [...document.querySelectorAll("div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']")];
      for (const el of rowEls) {
        const productCode = el.innerText?.trim();
        const row = el.id.match(/cell_(\d+)_0:text/)?.[1];
        
        // 현재 중분류 내에서 이미 본 코드이면 건너뜀
        if (!row || !productCode || seenCodesInMid.has(productCode)) continue;

        newProductsFoundInView = true;
        seenCodesInMid.add(productCode);

        const quantityStr = getText(row, 2);
        const quantity = parseInt(quantityStr.replace(/,/g, ""), 10) || 0;
        actualQuantity += quantity;

        const productObject = {
          midCode: midCode,
          midName: midName,
          productCode: productCode,
          productName: getText(row, 1),
          sales: quantity, // 매출 수량
          order_cnt: parseInt(getText(row, 3).replace(/,/g, ""), 10) || 0,
          purchase: parseInt(getText(row, 4).replace(/,/g, ""), 10) || 0,
          disposal: parseInt(getText(row, 5).replace(/,/g, ""), 10) || 0,
          stock: parseInt(getText(row, 6).replace(/,/g, ""), 10) || 0,
        };
        productDataForMid.push(productObject);

        // 조기 종료 로직 제거: 수량 일치해도 끝까지 스크롤
      }

      const scrollBtn = document.querySelector("div[id$='gdDetail.vscrollbar.incbutton:icontext']");
      if (!scrollBtn) break;

      const waitForChange = new Promise((resolve) => {
        const observer = new MutationObserver(() => { observer.disconnect(); resolve(true); });
        observer.observe(gridBody, { childList: true });
        setTimeout(() => { observer.disconnect(); resolve(false); }, 1500);
      });

      await clickElementById(scrollBtn.id);
      const changed = await waitForChange;

      if (changed) {
        noChangeScrolls = 0;
      } else {
        noChangeScrolls++;
      }
    }

    // 검증 결과 저장 및 콘솔 출력
    const verificationStatus = (expectedQuantity === actualQuantity) ? "일치" : "불일치";
    const verificationMessage = `[수량 ${verificationStatus}] ${midCode} (${midName}): 기대 ${expectedQuantity}, 실제 ${actualQuantity}`;
    
    window.automation.verificationResults.push({
        midCode: midCode,
        midName: midName,
        expectedQuantity: expectedQuantity,
        actualQuantity: actualQuantity,
        status: verificationStatus,
        message: verificationMessage
    });

    if (verificationStatus === "불일치") {
        console.warn(verificationMessage);
        // 불일치 시 수집된 상품 라인 전체를 로그에 출력
        console.warn(`[불일치 상세] ${midCode} (${midName}) 수집된 상품:`, productDataForMid);
    } else {
        console.log(verificationMessage);
    }

    return productDataForMid;
  }

  // 3. 메인 실행 함수 (대기 시간 최적화)
  async function autoClickAllMidCodesAndProducts() {
    await (async () => {
        for(let i=0; i<10; i++) {
            const el = document.querySelector("div[id*='gdList.body'][id*='cell_'][id$='_0:text']");
            if (el) return;
            await delay(300);
        }
        throw new Error("중분류 그리드를 찾을 수 없습니다.");
    })();
    
    const allProductsMap = new Map(); // 상품 코드를 키로 하는 Map
    const seenMid = new Set();
    let noChangeScrolls = 0;

    while (noChangeScrolls < 3) {
      const textCells = [...document.querySelectorAll("div[id*='gdList.body'][id*='cell_'][id$='_0:text']")];
      let foundNewMid = false;

      for (const textEl of textCells) {
        const code = textEl.innerText?.trim();
        if (!/^\d{3}$/.test(code) || seenMid.has(code)) continue;

        foundNewMid = true;
        seenMid.add(code);

        const rowIdx = textEl.id.match(/cell_(\d+)_0:text/)?.[1];
        const midName = getText(rowIdx, 1, "gdList");
        
        const expectedQuantityStr = getText(rowIdx, 2, "gdList");
        const expectedQuantity = parseInt(expectedQuantityStr.replace(/,/g, ""), 10) || 0;

        await clickElementById(textEl.id.split(":text")[0]);
        await delay(250);

        const productDataForMid = await collectProductDataForMid(code, midName, expectedQuantity);
        
        // 수집된 상품 데이터를 allProductsMap에 병합/갱신
        for (const product of productDataForMid) {
            if (allProductsMap.has(product.productCode)) {
                // 이미 존재하는 상품이면 sales 수량만 더함
                const existingProduct = allProductsMap.get(product.productCode);
                existingProduct.sales += product.sales;
                existingProduct.order_cnt += product.order_cnt;
                existingProduct.purchase += product.purchase;
                existingProduct.disposal += product.disposal;
                existingProduct.stock += product.stock;
            } else {
                // 새로운 상품이면 그대로 추가
                allProductsMap.set(product.productCode, product);
            }
        }
        break;
      }

      if (foundNewMid) {
        noChangeScrolls = 0;
        continue;
      }

      const scrollBtn = document.querySelector("div[id$='gdList.vscrollbar.incbutton:icontext']");
      if (!scrollBtn) break;
      
      await clickElementById(scrollBtn.id);
      await delay(500);
      noChangeScrolls++;
    }

    // Map의 값을 다시 탭으로 구분된 문자열 배열로 변환
    window.automation.parsedData = Array.from(allProductsMap.values()).map(product => {
        return [
            product.midCode, product.midName, product.productCode, product.productName,
            product.sales, product.order_cnt, product.purchase, product.disposal, product.stock
        ].join("\t");
    });

    console.log(`🎉 전체 수집 완료. 총 ${window.automation.parsedData.length}개 상품, ${seenMid.size}개 중분류.`);
  }

  window.automation.autoClickAllMidCodesAndProducts = autoClickAllMidCodesAndProducts;
})();