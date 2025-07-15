(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));
  const result = [];

  function downloadResult(data = result) {
    if (!Array.isArray(data) || data.length === 0) return;
    const lines = data
      .map(r =>
        [
          r.midCode,
          r.productCode,
          r.productName,
          r.sales,
          r.order,
          r.purchase,
          r.discard,
          r.stock,
        ].join("\t")
      )
      .join("\n");
    const blob = new Blob([lines], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "product_list.txt";
    a.click();
    URL.revokeObjectURL(url);
  }

  const existing = window.__parsedData__;
  if (Array.isArray(existing) && existing.length > 0) {
    downloadResult(existing);
    console.log("\uD83D\uDCC4 기존 데이터 다운로드 완료:", existing.length);
    return;
  }

  async function clickElementById(id) {
    const el = document.getElementById(id);
    if (!el) return false;
    const r = el.getBoundingClientRect();
    ["mousedown", "mouseup", "click"].forEach(type =>
      el.dispatchEvent(new MouseEvent(type, {
        bubbles: true,
        cancelable: true,
        view: window,
        clientX: r.left + r.width / 2,
        clientY: r.top + r.height / 2
      }))
    );
    return true;
  }

  function collectVisibleProducts(midCode, midText) {
    const cells = [...document.querySelectorAll("div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']")];
    for (const c of cells) {
      const m = c.id.match(/cell_(\d+)_0:text$/);
      if (!m) continue;
      const row = m[1];
      const getText = col => document.querySelector(
        `div[id*='gdDetail.body'][id*='cell_${row}_${col}:text']`
      )?.innerText?.trim() || "";
      result.push({
        midCode,
        midText,
        productCode: getText(0),
        productName: getText(1),
        sales: getText(2),
        order: getText(3),
        purchase: getText(4),
        discard: getText(5),
        stock: getText(6)
      });
    }
  }

  async function collectAllProducts() {
    const seen = new Set(result.map(r => r.productCode));
    let scrollCount = 0;
    while (true) {
      const rows = [...document.querySelectorAll("div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']")];
      let added = false;
      const midCell = document.querySelector("div[id*='gdList.body'][id*='cell_'][id$='_0:text'].nexagridcellfocused,div[id*='gdList.body'][id*='cell_'][id$='_0:text'].nexagridselected");
      const midCode = midCell?.innerText?.trim() || "";
      let midText = "";
      if (midCell) {
        const nameEl = document.getElementById(midCell.id.replace('_0:text','_1:text'));
        midText = nameEl?.innerText?.trim() || "";
      }
      for (const el of rows) {
        const m = el.id.match(/cell_(\d+)_0:text$/);
        if (!m) continue;
        const row = m[1];
        const code = el.innerText?.trim();
        if (!/^\d{13}$/.test(code)) continue;
        if (seen.has(code)) continue;
        const getText = col => document.querySelector(
          `div[id*='gdDetail.body'][id*='cell_${row}_${col}:text']`
        )?.innerText?.trim() || "";
        result.push({
          midCode,
          midText,
          productCode: code,
          productName: getText(1),
          sales: getText(2),
          order: getText(3),
          purchase: getText(4),
          discard: getText(5),
          stock: getText(6)
        });
        seen.add(code);
        added = true;
      }
      if (!added) break;
      const scrollBtn = document.querySelector("div[id$='gdDetail.vscrollbar.incbutton:icontext']");
      if (!scrollBtn) break;
      await clickElementById(scrollBtn.id);
      scrollCount++;
      console.log(`🔄 상품 스크롤 ${scrollCount}회`);
      await delay(1000);
    }
  }

  async function autoClickAllMidCodes() {
    const seenMid = new Set();
    let scrollCount = 0;
    while (true) {
      const cells = [...document.querySelectorAll("div[id*='gdList.body'][id*='cell_'][id$='_0:text']")];
      let found = false;
      for (const el of cells) {
        const code = el.innerText?.trim();
        if (!/^\d{3}$/.test(code) || seenMid.has(code)) continue;
        const clickId = el.id.replace(':text','');
        if (!await clickElementById(clickId)) {
          console.warn('❌ 중분류 클릭 대상 없음 → ID:', clickId);
          continue;
        }
        seenMid.add(code);
        found = true;
        await delay(500);
        const nameEl = document.getElementById(el.id.replace('_0:text','_1:text'));
        const midText = nameEl?.innerText?.trim() || '';
        collectVisibleProducts(code, midText);
        await collectAllProducts();
        await delay(300);
      }
      if (!found) break;
      const scrollBtn = document.querySelector("div[id$='gdList.vscrollbar.incbutton:icontext']");
      if (!scrollBtn) break;
      await clickElementById(scrollBtn.id);
      scrollCount++;
      console.log(`🔄 중분류 스크롤 ${scrollCount}회`);
      await delay(1000);
    }
  }

  autoClickAllMidCodes().then(() => {
    window.__parsedData__ = result;
    downloadResult(result);
    console.log('🎉 전체 작업 완료:', result.length);
  });
})();

