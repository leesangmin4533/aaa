(() => {
  // 1. 네임스페이스 및 유틸리티 설정
  window.automation = {
    logs: [],
    parsedData: null,
    error: null,
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

  // 전체 수집 과정에서 이미 처리된 상품 코드를 추적하는 Set
  const seenAllProductCodes = new Set();

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

    const productLines = [];
    const seenCodesInMid = new Set(); // 현재 중분류 내에서만 본 상품 코드
    let actualQuantity = 0;
    let noChangeScrolls = 0;

    while (noChangeScrolls < 3) {
      let newProductsFoundInView = false;

      const rowEls = [...document.querySelectorAll("div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']")];
      for (const el of rowEls) {
        const code = el.innerText?.trim();
        const row = el.id.match(/cell_(\d+)_0:text/)?.[1];
        
        // 현재 중분류 내에서 이미 본 코드이거나, 전체 수집 과정에서 이미 본 코드이면 건너뜀
        if (!row || !code || seenCodesInMid.has(code) || seenAllProductCodes.has(code)) continue;

        newProductsFoundInView = true;
        seenCodesInMid.add(code);
        seenAllProductCodes.add(code); // 전체 상품 코드 Set에 추가

        const quantityStr = getText(row, 2);
        const quantity = parseInt(quantityStr.replace(/,/g, ""), 10) || 0;
        actualQuantity += quantity;

        const line = [
          midCode, midName, getText(row, 0), getText(row, 1), quantityStr,
          getText(row, 3), getText(row, 4), getText(row, 5), getText(row, 6),
        ].join("\t");
        productLines.push(line);
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

    if (expectedQuantity !== actualQuantity) {
      console.warn(`[수량 불일치] ${midCode} (${midName}): 기대 ${expectedQuantity}, 실제 ${actualQuantity}`);
    } else {
      console.log(`[수량 일치] ${midCode} (${midName}): ${actualQuantity}`);
    }

    return productLines;
  }

  // 3. 메인 실행 함수 (대기 시간 최적화)
  async function autoClickAllMidCodesAndProducts() {
    await (async () => {
        for(let i=0; i<10; i++) {
            if (document.querySelector("div[id*='gdList.body'][id*='cell_'][id$='_0:text']")) return;
            await delay(300);
        }
        throw new Error("중분류 그리드를 찾을 수 없습니다.");
    })();
    
    const allData = [];
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

        const productData = await collectProductDataForMid(code, midName, expectedQuantity);
        allData.push(...productData);
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

    window.automation.parsedData = allData;
    console.log(`🎉 전체 수집 완료. 총 ${allData.length}개 상품, ${seenMid.size}개 중분류.`);
  }

  window.automation.autoClickAllMidCodesAndProducts = autoClickAllMidCodesAndProducts;
})();