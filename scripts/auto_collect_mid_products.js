(() => {
  window.__midCategoryLogs__ = [];
  const origConsoleLog = console.log;
  console.log = function (...args) {
    window.__midCategoryLogs__.push(args.join(" "));
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
          return reject('⛔ gdList 로딩 시간 초과');
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
    const productLines = [];
    const rowEls = [...document.querySelectorAll("div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']")];
    const rowIndices = Array.from(new Set(rowEls.map(el => el.id.match(/cell_(\d+)_0:text/)?.[1])));

    for (const row of rowIndices) {
      // 상품코드 셀 클릭 후 텍스트 수집
      const codeCellId = [...document.querySelectorAll(`div[id*='gdDetail.body'][id*='cell_${row}_0'][id$=':text']`)][0]?.id;
      const clickId = codeCellId?.split(":text")[0];
      if (clickId) {
        await clickElementById(clickId);
      } else {
        console.warn("❌ 상품코드 셀 ID 찾을 수 없음:", row);
      }

      const line = [
        midCode,
        midName,
        getText(row, 0),
        getText(row, 1),
        getText(row, 2),
        getText(row, 3),
        getText(row, 4),
        getText(row, 5),
        getText(row, 6)
      ].join("\t");
      productLines.push(line);

      await delay(100);
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
    const seenMid = new Set();
    let scrollCount = 0;

    while (true) {
      const textCells = [...document.querySelectorAll("div[id*='gdList.body'][id*='cell_'][id$='_0:text']")];
      const newMids = [];

      for (const textEl of textCells) {
        const code = textEl.innerText?.trim();
        if (!/^\d{3}$/.test(code) || seenMid.has(code)) continue;
        if ((startCode && code < startCode) || (endCode && code > endCode)) continue;

        const rowIdx = textEl.id.match(/cell_(\d+)_0:text/)?.[1];
        const midNameEl = document.querySelector(`div[id*='gdList.body'][id*='cell_${rowIdx}_1'][id$=':text']`);
        const midName = midNameEl?.innerText?.trim() || '';

        const clickId = textEl.id.split(":text")[0];
        const clicked = await clickElementById(clickId);
        if (!clicked) {
          console.warn("❌ 중분류 클릭 실패 → ID:", clickId);
          continue;
        }

        seenMid.add(code);
        newMids.push(code);
        console.log(`✅ 중분류 클릭: ${code} (${midName})`);
        await delay(500);

        await collectProductDataForMid(code, midName);
        await delay(300);
      }

      if (newMids.length === 0) {
        console.warn("📌 더 이상 새로운 중분류 없음 → 종료");
        break;
      }

      const scrollBtn = document.querySelector("div[id$='gdList.vscrollbar.incbutton:icontext']");
      if (!scrollBtn) {
        console.warn("❌ 중분류 스크롤 버튼 없음 → 종료");
        break;
      }

      await clickElementById(scrollBtn.id);
      scrollCount++;
      console.log(`🔄 중분류 스크롤 ${scrollCount}회`);
      await delay(1000);
    }

    console.log("🎉 전체 수집 완료 → 총 중분류 수:", seenMid.size);
    console.log("📄 전체 데이터 누적:", midCodeDataList.length, "줄");
    window.__parsedData__ = midCodeDataList;
  }

  window.collectMidProducts = collectMidCodes;

  (async () => {
    try {
      await waitForMidGrid();
      await collectMidCodes();
    } catch (e) {
      console.warn(e);
    }
  })();
})();
