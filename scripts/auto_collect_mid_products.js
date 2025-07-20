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
    return el?.innerText?.trim() || '';
  }


  async function collectProductDataForMid(midCode, midName) {
    document.dispatchEvent(
      new CustomEvent('mid-clicked', { detail: { code: midCode, midName } })
    );
    const productLines = [];
    const seenCodes = new Set();

    while (true) {
      const rowEls = [
        ...document.querySelectorAll(
          "div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']"
        )
      ];
      let newCount = 0;

      for (const el of rowEls) {
        const code = el.innerText?.trim();
        const row = el.id.match(/cell_(\d+)_0:text/)?.[1];
        if (!row || !code || seenCodes.has(code)) continue;

        const clickId = el.id.split(":text")[0];
        if (clickId) {
          await clickElementById(clickId);
        } else {
          console.warn("상품코드 셀 ID 찾을 수 없음:", row);
        }

        const line = [
          midCode,
          midName,
          getText(row, 0) || '0',
          getText(row, 1) || '0',
          getText(row, 2) || '0',
          getText(row, 3) || '0',
          getText(row, 4) || '0',
          getText(row, 5) || '0',
          getText(row, 6) || '0'
        ].join("\t");

        seenCodes.add(code);
        productLines.push(line);
        newCount++;
        await delay(100);
      }

      const scrollBtn = document.querySelector(
        "div[id$='gdDetail.vscrollbar.incbutton:icontext']"
      );

      if (!scrollBtn) break;

      if (newCount === 0) {
        // 스크롤 전후 변화가 없으면 종료
        const lastCode = rowEls[rowEls.length - 1]?.innerText?.trim();
        await clickElementById(scrollBtn.id);
        await delay(500);
        document.dispatchEvent(
          new CustomEvent('product-scroll', { detail: { midCode } })
        );
        const afterRows = [
          ...document.querySelectorAll(
            "div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']"
          )
        ];
        const afterLast = afterRows[afterRows.length - 1]?.innerText?.trim();
        if (afterLast === lastCode) break;
        continue;
      }

      await clickElementById(scrollBtn.id);
      await delay(500);
      document.dispatchEvent(
        new CustomEvent('product-scroll', { detail: { midCode } })
      );
    }

    midCodeDataList.push(...productLines);
    console.log(productLines.join("\n"));
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

    while (true) {
      console.log("🔄 중분류 목록 스캔 시작");
      const textCells = [...document.querySelectorAll("div[id*='gdList.body'][id*='cell_'][id$='_0:text']")];
      console.log(`Found ${textCells.length} mid-category cells.`);
      const newMids = [];

      for (const textEl of textCells) {
        const code = textEl.innerText?.trim();
        if (!/^\d{3}$/.test(code) || seenMid.has(code)) continue;
        if ((startCode && code < startCode) || (endCode && code > endCode)) continue;

        const rowIdx = textEl.id.match(/cell_(\d+)_0:text/)?.[1];

        async function getMidName(rowIdx, attempts = 10) {
          for (let i = 0; i < attempts; i++) {
            const el = document.querySelector(
              `div[id*='gdList.body'][id*='cell_${rowIdx}_1'][id$=':text']`
            );
            const name = el?.innerText?.trim();
            if (name) return name;
            await delay(300);
          }
          return '';
        }

        const clickId = textEl.id.split(":text")[0];
        console.log(`Attempting to click mid-category: ${code} with ID: ${clickId}`);
        const clicked = await clickElementById(clickId);
        if (!clicked) {
          console.warn("중분류 클릭 실패 → ID:", clickId);
          continue;
        }

        const midName = await getMidName(rowIdx);

        seenMid.add(code);
        newMids.push(code);
        console.log(`중분류 클릭: ${code} (${midName})`);
        await delay(500);

        console.log(`Collecting product data for mid-category: ${code}`);
        await collectProductDataForMid(code, midName);
        console.log(`Finished collecting product data for mid-category: ${code}`);
        await delay(300);
      }

      if (newMids.length === 0) {
        console.warn("더 이상 새로운 중분류 없음 → 종료");
        break;
      }

      const scrollBtn = document.querySelector("div[id$='gdList.vscrollbar.incbutton:icontext']");
      if (!scrollBtn) {
        console.warn("중분류 스크롤 버튼 없음 → 종료");
        break;
      }

      await clickElementById(scrollBtn.id);
      scrollCount++;
      console.log(`🔄 중분류 스크롤 ${scrollCount}회`);
      await delay(1000);
    }

    console.log("🎉 전체 수집 완료 → 총 중분류 수:", seenMid.size);
    console.log("📄 전체 데이터 누적:", midCodeDataList.length, "줄");
    window.automation.parsedData = midCodeDataList;
  }

  window.collectMidProducts = collectMidCodes;

  (async () => {
    try {
      await waitForMidGrid();
      await collectMidCodes();
    } catch (e) {
      console.warn(e);
      window.automation.error = e && e.message ? e.message : String(e);
    }
  })();
})();
