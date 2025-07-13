(async () => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  const seenMidCodes = new Set();
  const logs = [];
  const scrollLogs = [];
  const rowLogs = [];
  const finalData = [];

  const parseNumber = cell => {
    if (!cell) return 0;
    const txt = cell.innerText.replace(/,/g, '').trim();
    return txt === '' ? 0 : Number(txt);
  };

  const scrollAndWait = async selector => {
    const btn = document.querySelector(selector);
    if (btn) {
      const r = btn.getBoundingClientRect();
      ['mousedown', 'mouseup', 'click'].forEach(t => btn.dispatchEvent(
        new MouseEvent(t, {
          bubbles: true,
          cancelable: true,
          view: window,
          clientX: r.left + r.width / 2,
          clientY: r.top + r.height / 2,
        })
      ));
      await delay(1000);
      scrollLogs.push({ selector, status: 'success' });
      return true;
    }
    scrollLogs.push({ selector, status: 'not-found' });
    return false;
  };

  const parseRow = (midCode, idx) => {
    const codeCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${idx}_0'][id$=':text']`);
    if (!codeCell) {
      rowLogs.push({ midCode, idx, cell: 'code', status: 'not-found' });
      console.warn(`❌ 코드 셀 탐색 실패 → ${midCode} / ${idx}`);
      return null;
    }

    const nameCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${idx}_1'][id$=':text']`);
    if (!nameCell) {
      rowLogs.push({ midCode, idx, cell: 'name', status: 'not-found' });
      console.warn(`❌ 이름 셀 탐색 실패 → ${midCode} / ${idx}`);
    }

    const salesCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${idx}_2'][id$=':text']`);
    if (!salesCell) {
      rowLogs.push({ midCode, idx, cell: 'sales', status: 'not-found' });
      console.warn(`❌ 판매 셀 탐색 실패 → ${midCode} / ${idx}`);
    }

    const orderCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${idx}_3'][id$=':text']`);
    if (!orderCell) {
      rowLogs.push({ midCode, idx, cell: 'order', status: 'not-found' });
      console.warn(`❌ 주문 셀 탐색 실패 → ${midCode} / ${idx}`);
    }

    const purchaseCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${idx}_4'][id$=':text']`);
    if (!purchaseCell) {
      rowLogs.push({ midCode, idx, cell: 'purchase', status: 'not-found' });
      console.warn(`❌ 매입 셀 탐색 실패 → ${midCode} / ${idx}`);
    }

    const discardCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${idx}_5'][id$=':text']`);
    if (!discardCell) {
      rowLogs.push({ midCode, idx, cell: 'discard', status: 'not-found' });
      console.warn(`❌ 폐기 셀 탐색 실패 → ${midCode} / ${idx}`);
    }

    const stockCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${idx}_6'][id$=':text']`);
    if (!stockCell) {
      rowLogs.push({ midCode, idx, cell: 'stock', status: 'not-found' });
      console.warn(`❌ 재고 셀 탐색 실패 → ${midCode} / ${idx}`);
    }

    return {
      midCode,
      productCode: codeCell.innerText.trim(),
      productName: nameCell ? nameCell.innerText.trim() : '',
      sales: parseNumber(salesCell),
      order: parseNumber(orderCell),
      purchase: parseNumber(purchaseCell),
      discard: parseNumber(discardCell),
      stock: parseNumber(stockCell),
    };
  };

  const processProducts = async midCode => {
    const seenProductCodes = new Set();
    let dupCount = 0;

    while (true) {
      const cells = [...document.querySelectorAll("div[id*='gdDetail.body'][id$='_0:text']")];
      for (const cell of cells) {
        const code = cell.innerText.trim();
        if (seenProductCodes.has(code)) {
          dupCount += 1;
          if (dupCount >= 3 && !document.querySelector("div[id$='gdDetail.vscrollbar.incbutton:icontext']")) {
            return;
          }
          continue;
        }
        dupCount = 0;
        seenProductCodes.add(code);
        const idxMatch = cell.id.match(/cell_(\d+)_0/);
        const idx = idxMatch ? Number(idxMatch[1]) : 0;
        const row = parseRow(midCode, idx);
        if (row) finalData.push(row);
      }
      if (dupCount >= 3 && !document.querySelector("div[id$='gdDetail.vscrollbar.incbutton:icontext']")) break;
      if (!(await scrollAndWait("div[id$='gdDetail.vscrollbar.incbutton:icontext']"))) {
        await delay(1000);
      }
    }
  };

  let midDupCount = 0;
  while (true) {
    const cells = [...document.querySelectorAll("div[id*='gdList.body'][id$='_0:text']")];
    for (const cell of cells) {
      const code = cell.innerText.trim();
      if (!/^\d{3}$/.test(code)) continue;
      if (seenMidCodes.has(code)) {
        midDupCount += 1;
        if (midDupCount >= 3 && !document.querySelector("div[id$='gdList.vscrollbar.incbutton:icontext']")) {
          window.__midCategoryLogs__ = logs;
          window.__parsedData__ = finalData;
          return;
        }
        continue;
      }
      midDupCount = 0;
      seenMidCodes.add(code);

      const clickId = cell.id.replace(':text', '');
      const clickEl = document.getElementById(clickId);
      if (!clickEl) {
        logs.push({ code, status: 'not-found' });
        continue;
      }
      const rect = clickEl.getBoundingClientRect();
      ['mousedown', 'mouseup', 'click'].forEach(t => clickEl.dispatchEvent(
        new MouseEvent(t, {
          bubbles: true,
          cancelable: true,
          view: window,
          clientX: rect.left + rect.width / 2,
          clientY: rect.top + rect.height / 2,
        })
      ));
      logs.push({ code, status: 'success' });

      let ready = false;
      for (let i = 0; i < 10; i++) {
        await delay(200);
        const exists = document.querySelector("div[id*='gdDetail.body'][id*='cell_0_0'][id$=':text']");
        if (exists) { ready = true; break; }
      }
      if (!ready) continue;
      await processProducts(code);
    }

    if (midDupCount >= 3 && !document.querySelector("div[id$='gdList.vscrollbar.incbutton:icontext']")) break;
    if (!(await scrollAndWait("div[id$='gdList.vscrollbar.incbutton:icontext']"))) {
      await delay(1000);
    }
  }

  window.__midCategoryLogs__ = logs;
  window.__scrollLogs__ = scrollLogs;
  window.__rowLogs__ = rowLogs;
  window.__parsedData__ = finalData;
})();
