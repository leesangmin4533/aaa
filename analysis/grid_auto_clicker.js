(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  const HEADER = [
    "중분류코드",
    "중분류텍스트",
    "상품코드",
    "상품명",
    "매출",
    "발주",
    "매입",
    "폐기",
    "현재고",
  ];

  window.__exportedRows = [];

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

  function collectRowData(rowIdx, midCode, midName) {
    const row = {
      [HEADER[0]]: midCode,
      [HEADER[1]]: midName,
    };
    for (let c = 0; c < HEADER.length - 2; c++) {
      const cell = document.querySelector(
        `div[id^='gdDetail.gridrow_0.cell_${rowIdx}_${c}:text']`
      );
      row[HEADER[c + 2]] = cell ? cell.innerText.trim() : "";
    }
    window.__exportedRows.push(row);
  }

  async function autoClickAllProductCodes(midCode, midName) {
    const seen = new Set();
    let scrollCount = 0;

    while (true) {
      const textCells = [...document.querySelectorAll("div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']")];
      const newCodes = [];

      for (const textEl of textCells) {
        const code = textEl.innerText?.trim();
        if (!/^\d{13}$/.test(code)) continue;
        if (seen.has(code)) continue;

        const rowIdx = textEl.id.match(/cell_(\d+)_0:text$/)?.[1];
        if (rowIdx !== undefined) {
          collectRowData(rowIdx, midCode, midName);
        }

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

        const idx = textEl.id.match(/gridrow_(\d+)/)?.[1];
        const nameEl = idx
          ? document.querySelector(`div[id="gdList.gridrow_${idx}.cell_${idx}_1:text"]`)
          : null;
        const midName = nameEl ? nameEl.innerText.trim() : "";

        seenMid.add(code);
        newMids.push(code);
        console.log(`✅ 중분류 클릭 완료: ${code}`);
        await delay(500);  // 중분류 클릭 후 화면 렌더링 대기

        await autoClickAllProductCodes(code, midName); // 상품코드 클릭 루프 진입
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
