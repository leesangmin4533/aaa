(async () => {
  const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
  const seen = new Set();
  const logs = [];
  const finalData = [];

  const textCells = [...document.querySelectorAll("div[id*='gdList.body'][id$='_0:text']")];

  for (const textEl of textCells) {
    const code = textEl.innerText?.trim();
    if (!/^\d{3}$/.test(code) || seen.has(code)) continue;

    const clickId = textEl.id.replace(':text', '');
    const clickEl = document.getElementById(clickId);
    if (!clickEl) {
      logs.push({ code, status: 'not-found' });
      continue;
    }

    const rect = clickEl.getBoundingClientRect();
    ['mousedown', 'mouseup', 'click'].forEach(type => {
      clickEl.dispatchEvent(new MouseEvent(type, {
        bubbles: true, cancelable: true, view: window,
        clientX: rect.left + rect.width / 2,
        clientY: rect.top + rect.height / 2
      }));
    });

    logs.push({ code, status: 'success' });
    seen.add(code);
    console.log(`✅ 중분류 클릭됨 → ${code}`);

    let ready = false;
    for (let i = 0; i < 10; i++) {
      await delay(200);
      const exists = document.querySelector("div[id*='gdDetail.body'][id*='cell_0_0'][id$=':text']");
      if (exists) { ready = true; break; }
    }
    if (!ready) {
      console.warn(`❌ 상품 로딩 실패 → ${code}`);
      continue;
    }

    const rows = [];
    for (let i = 0; ; i++) {
      const codeCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${i}_0'][id$=':text']`);
      if (!codeCell) break;
      const nameCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${i}_1'][id$=':text']`);
      rows.push({
        midCode: code,
        productCode: codeCell.innerText.trim(),
        productName: nameCell ? nameCell.innerText.trim() : ''
      });
    }
    finalData.push(...rows);
  }

  window.__midCategoryLogs__ = logs;
  window.__parsedData__ = finalData;
})();
