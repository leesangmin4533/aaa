(() => {
  window.automation = {
    logs: [],
    parsedData: null,
    error: null
  };
  async function autoClickAllMidCodesAndProducts(startCode = null, endCode = null) {
    await waitForMidGrid();
    await collectMidCodes(startCode, endCode);
  }

  window.collectMidProducts = collectMidCodes;
  window.automation.autoClickAllMidCodesAndProducts = autoClickAllMidCodesAndProducts;
  const origConsoleLog = console.log;
  console.log = function (...args) {
    window.automation.logs.push(args.join(" "));
    return origConsoleLog.apply(console, args);
  };
  const delay = ms => new Promise(res => setTimeout(res, ms));
  const midCodeDataList = [];

  function waitForMidGrid(maxWait = 10000) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      const check = () => {
        const cells = document.querySelectorAll(
          "div[id*='gdList.body'][id*='cell_'][id$='_0:text']"
        );
        if (cells.length > 0) return resolve(true);
        if (Date.now() - start > maxWait) {
          return reject('gdList 로딩 시간 초과');
        }
        setTimeout(check, 300);
      };
      check();
    });
  }

  function getText(row, col) {
    const el = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${row}_${col}'][id$=':text']`);
    const text = el?.innerText?.trim() || '';
    console.log(`[getText] Row: ${row}, Col: ${col}, Text: '${text}'`); // 디버그 로그 유지
    return text;
  }

  function getMidListText(row, col) {
    const el = document.querySelector(`div[id*='gdList.body'][id*='cell_${row}_${col}'][id$=':text']`);
    return el?.innerText?.trim() || '';
  }


  async function collectProductDataForMid(midCode, midName, expectedTotalSales) { // 변수명 변경
    console.log(`[collectProductDataForMid] Starting for mid-category: ${midCode} (${midName}). Expected total sales: ${expectedTotalSales}`); // 로그 메시지 변경
    document.dispatchEvent(
      new CustomEvent('mid-clicked', { detail: { code: midCode, midName } })
    );
    // Wait for gdDetail grid to load for the current mid-category
    await waitForElement(`div[id*='gdDetail.body'][id*='cell_0_0'][id$=':text']`, 30000); // 타임아웃 30초로 증가
    await delay(500); // 그리드 렌더링을 위한 추가 대기
    const productLines = [];
    const seenCodes = new Set();
    let consecutiveNoNewDataScrolls = 0;
    let actualTotalSales = 0; // 변수명 변경

    while (true) {
      console.log(`[collectProductDataForMid] Scanning products in current view for mid-category: ${midCode}`);
      const rowEls = [
        ...document.querySelectorAll(
          "div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']"
        )
      ];
      let newCount = 0;
      const currentProductCodes = new Set();

      if (rowEls.length === 0) {
        console.log(`[collectProductDataForMid] No product rows found for mid-category: ${midCode}. Ending collection for this mid-category.`);
        break;
      }

      for (const el of rowEls) {
        const code = el.innerText?.trim();
        const row = el.id.match(/cell_(\d+)_0:text/)?.[1];
        console.log(`[collectProductDataForMid] Examining product cell: ${code} at row: ${row}`);
        if (!row || !code) {
          console.warn("[collectProductDataForMid] Skipping malformed or empty product row.");
          continue;
        }
        currentProductCodes.add(code);

        if (seenCodes.has(code)) {
          console.log(`[collectProductDataForMid] Product ${code} already seen. Skipping.`);
          continue;
        }

        console.log(`[collectProductDataForMid] Processing new product: ${code} in row ${row}`);

        const clickId = el.id.split(":text")[0];
        if (clickId) {
          console.log(`[collectProductDataForMid] Attempting to click product element with ID: ${clickId}`);
          await clickElementById(clickId);
          console.log(`[collectProductDataForMid] Successfully clicked product element.`);
        } else {
          console.warn("상품코드 셀 ID 찾을 수 없음:", row);
        }

        const line = [
          midCode,
          midName,
          getText(row, 0) || '0',
          getText(row, 1) || '0',
          getText(row, 2) || '0', // 매출
          getText(row, 3) || '0', // 발주
          getText(row, 4) || '0', // 매입
          getText(row, 5) || '0', // 폐기
          getText(row, 6) || '0'  // 현재고
        ].join("\t");

        // Add sales to actualTotalSales (매출액을 합산)
        const salesValRaw = getText(row, 2) || '0'; // 매출액은 인덱스 2
        const salesVal = parseInt(salesValRaw, 10);
        console.log(`[collectProductDataForMid] Product ${code}: salesValRaw = '${salesValRaw}', parsed salesVal = ${salesVal}`); // 디버그 로그 유지
        if (!isNaN(salesVal)) {
          actualTotalSales += salesVal;
        }

        seenCodes.add(code);
        productLines.push(line);
        newCount++;
        console.log(`[collectProductDataForMid] Added product ${code}. Total new in this cycle: ${newCount}. Total collected: ${productLines.length}`);
        await delay(100);
      }

      const scrollBtn = document.querySelector(
        "div[id$='gdDetail.vscrollbar.incbutton:icontext']"
      );

      if (!scrollBtn) {
        console.log("[collectProductDataForMid] Product scroll button not found. Ending collection for this mid-category.");
        break;
      }

      if (newCount > 0) {
        consecutiveNoNewDataScrolls = 0;
        console.log(`[collectProductDataForMid] Found ${newCount} new products. Resetting no-new-data counter.`);
      } else {
        console.log("[collectProductDataForMid] No new products found in current view. Attempting to scroll.");
        const beforeScrollProductCodes = new Set(currentProductCodes);
        console.log(`[collectProductDataForMid] Before scroll products: ${Array.from(beforeScrollProductCodes).join(', ')}`);

        console.log(`[collectProductDataForMid] Clicking product scroll button with ID: ${scrollBtn.id}`);
        await clickElementById(scrollBtn.id);
        await delay(1000);
        document.dispatchEvent(
          new CustomEvent('product-scroll', { detail: { midCode } })
        );
        console.log("[collectProductDataForMid] Scrolled. Checking for new visible products.");

        const afterScrollRowEls = [
          ...document.querySelectorAll(
            "div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']"
          )
        ];
        const afterScrollProductCodes = new Set();
        for (const el of afterScrollRowEls) {
          const code = el.innerText?.trim();
          if (code) afterScrollProductCodes.add(code);
        }
        console.log(`[collectProductDataForMid] After scroll products: ${Array.from(afterScrollProductCodes).join(', ')}`);

        const hasChanged = !(beforeScrollProductCodes.size === afterScrollProductCodes.size &&
                             [...beforeScrollProductCodes].every(code => afterScrollProductCodes.has(code)));

        if (!hasChanged) {
          consecutiveNoNewDataScrolls++;
          console.log(`[collectProductDataForMid] Scroll did not yield new visible products. Consecutive no-change scrolls: ${consecutiveNoNewDataScrolls}`);
          if (consecutiveNoNewDataScrolls >= 5) {
            console.log("[collectProductDataForMid] Reached 3 consecutive scrolls with no new visible products. Ending collection for this mid-category.");
            break;
          }
        } else {
          consecutiveNoNewDataScrolls = 0;
          console.log("[collectProductDataForMid] Scroll yielded new visible products. Resetting no-new-data counter.");
        }
      }
    }

    midCodeDataList.push(...productLines);
    console.log(`[collectProductDataForMid] Finished for mid-category ${midCode}. Total products collected: ${productLines.length}`);

    // Compare expected and actual total sales (매출 총합 비교)
    if (expectedTotalSales !== null && actualTotalSales !== expectedTotalSales) {
      console.warn(`[collectProductDataForMid] Mismatch for mid-category ${midCode} (${midName}): Expected total sales = ${expectedTotalSales}, Actual total sales = ${actualTotalSales}`); // 로그 메시지 변경
    } else if (expectedTotalSales !== null) {
      console.log(`[collectProductDataForMid] Total sales matched for mid-category ${midCode} (${midName}): ${actualTotalSales}`); // 로그 메시지 변경
    }
  }

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

  async function collectMidCodes(startCode = null, endCode = null) {
    console.log("collectMidCodes 시작");
    const seenMid = new Set();
    let scrollCount = 0;
    let consecutiveNoNewMidScrolls = 0;

    while (consecutiveNoNewMidScrolls < 5) { // Exit condition
      console.log("🔄 중분류 목록 스캔 시작 (새로운 스크롤 주기)");
      const textCells = [...document.querySelectorAll("div[id*='gdList.body'][id*='cell_'][id$='_0:text']")];
      console.log(`Found ${textCells.length} mid-category cells in current view.`);
      
      let foundAndProcessedNewMid = false;

      for (const textEl of textCells) {
        const code = textEl.innerText?.trim();
        console.log(`[collectMidCodes] Examining mid-category cell: ${code}`);
        if (!/^\d{3}$/.test(code) || seenMid.has(code)) {
          console.log(`[collectMidCodes] Skipping mid-category: ${code} (Invalid format or already seen).`);
          continue;
        }
        if ((startCode && code < startCode) || (endCode && code > endCode)) {
          console.log(`[collectMidCodes] Skipping mid-category: ${code} (Outside of specified range).`);
          continue;
        }

        // Found a new mid-category to process
        const rowIdx = textEl.id.match(/cell_(\d+)_0:text/)?.[1];
        console.log(`[collectMidCodes] Identified mid-category: ${code} at row index: ${rowIdx}`);

        async function getMidName(rowIdx, attempts = 10) {
          console.log(`[getMidName] Attempting to get mid-category name for row: ${rowIdx}`);
          for (let i = 0; i < attempts; i++) {
            const el = document.querySelector(
              `div[id*='gdList.body'][id*='cell_${rowIdx}_1'][id$=':text']`
            );
            const name = el?.innerText?.trim();
            if (name) {
              console.log(`[getMidName] Successfully retrieved name: ${name}`);
              return name;
            }
            console.log(`[getMidName] Name not found for row ${rowIdx}, retrying (${i + 1}/${attempts})...`);
            await delay(300);
          }
          console.warn(`[getMidName] Failed to retrieve name for row ${rowIdx} after ${attempts} attempts.`);
          return '';
        }

        const clickId = textEl.id.split(":text")[0];
        console.log(`Attempting to click mid-category: ${code} with ID: ${clickId}`);
        const clicked = await clickElementById(clickId);
        if (!clicked) {
          console.warn("중분류 클릭 실패 → ID:", clickId);
          continue;
        }
        console.log(`Successfully clicked mid-category: ${code}.`);

        const midName = await getMidName(rowIdx);
        const expectedTotalSales = parseInt(getMidListText(rowIdx, 2) || '0', 10);
        if (isNaN(expectedTotalSales)) {
          console.warn(`[collectMidCodes] Could not parse expected total sales for mid-category ${code}. Using 0.`);
        }

        seenMid.add(code);
        console.log(`중분류 클릭: ${code} (${midName})`);
        console.log(`[DEBUG] Before delay after mid-category click.`);
        await delay(500);
        console.log(`[DEBUG] After delay after mid-category click.`);

        console.log(`[DEBUG] Before calling collectProductDataForMid for ${code} (${midName})...`);
        await collectProductDataForMid(code, midName, expectedTotalSales);
        console.log(`[DEBUG] After calling collectProductDataForMid for ${code} (${midName}).`);
        
        foundAndProcessedNewMid = true;
        // Break the inner for-loop to restart the scan from the top of the while-loop
        // This ensures we always work with a fresh list of elements
        break; 
      }

      if (foundAndProcessedNewMid) {
        consecutiveNoNewMidScrolls = 0; // Reset scroll counter
        continue; // Restart the while loop to scan for the next item
      }

      // If we reach here, no new mid-categories were found in the current view. We need to scroll.
      console.log("현재 뷰에 새로운 중분류 없음. 스크롤 시도.");
      const scrollBtn = document.querySelector("div[id$='gdList.vscrollbar.incbutton:icontext']");
      if (!scrollBtn) {
        console.warn("중분류 스크롤 버튼 없음 → 종료");
        break;
      }

      const lastCodeBeforeScroll = [...document.querySelectorAll("div[id*='gdList.body'][id*='cell_'][id$='_0:text']")].pop()?.innerText?.trim();

      console.log(`Attempting to click mid-category scroll button with ID: ${scrollBtn.id}`);
      await clickElementById(scrollBtn.id);
      scrollCount++;
      console.log(`🔄 중분류 스크롤 ${scrollCount}회 완료.`);
      await delay(1000); // Wait for scroll to take effect

      const lastCodeAfterScroll = [...document.querySelectorAll("div[id*='gdList.body'][id*='cell_'][id$='_0:text']")].pop()?.innerText?.trim();

      if (lastCodeBeforeScroll === lastCodeAfterScroll) {
        consecutiveNoNewMidScrolls++;
        console.log(`스크롤 후에도 새로운 중분류가 표시되지 않음. 연속 ${consecutiveNoNewMidScrolls}회.`);
      } else {
        consecutiveNoNewMidScrolls = 0;
      }
    }

    if(consecutiveNoNewMidScrolls >= 5) {
        console.log("5회 연속 스크롤해도 새로운 중분류가 없어 수집을 종료합니다.");
    }

    console.log("🎉 전체 중분류 수집 완료 → 총 중분류 수:", seenMid.size);
    console.log("📄 전체 데이터 누적:", midCodeDataList.length, "줄");
    window.automation.parsedData = midCodeDataList;
  }  })();