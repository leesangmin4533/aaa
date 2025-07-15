(async () => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  async function clickElementById(id) {
    const el = document.getElementById(id);
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    ["mousedown", "mouseup", "click"].forEach(type =>
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

  async function collectVisibleProductsWithMid(midRowIdx) {
    const list = (window.__productList = window.__productList || []);
    const midCodeEl = document.querySelector(
      `div[id*='gdList.body'][id*='cell_${midRowIdx}_0'][id$=':text']`
    );
    const midTextEl = document.querySelector(
      `div[id*='gdList.body'][id*='cell_${midRowIdx}_1'][id$=':text']`
    );
    const midCode = midCodeEl?.innerText?.trim() || '';
    const midText = midTextEl?.innerText?.trim() || '';

    let attempts = 0;
    while (
      !document.querySelector("div[id*='gdDetail.body'][id*='gridrow_0']") &&
      attempts++ < 15
    ) {
      await delay(300);
    }

    const rows = [
      ...document.querySelectorAll(
        "div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']"
      ),
    ];

    for (const codeEl of rows) {
      const match = codeEl.id.match(/cell_(\d+)_0:text$/);
      if (!match) continue;
      const rowIdx = match[1];
      const getText = col =>
        document.querySelector(
          `div[id*='gdDetail.body'][id*='cell_${rowIdx}_${col}:text']`
        )?.innerText?.trim() || '';

      list.push({
        midCode,
        midText,
        productCode: getText(0),
        productName: getText(1),
        sales: getText(2),
        order: getText(3),
        purchase: getText(4),
        discard: getText(5),
        stock: getText(6),
      });
    }
  }

  async function autoClickMidRange(startRow, endRow) {
    window.__productList = [];

    for (let rowIdx = startRow; rowIdx <= endRow; rowIdx++) {
      const codeEl = document.querySelector(
        `div[id*='gdList.body'][id*='cell_${rowIdx}_0'][id$=':text']`
      );
      if (!codeEl) continue;

      const clickId = codeEl.id.replace(":text", "");
      const target = document.getElementById(clickId);
      if (!target) continue;

      const rect = target.getBoundingClientRect();
      ["mousedown", "mouseup", "click"].forEach(evt =>
        target.dispatchEvent(
          new MouseEvent(evt, {
            bubbles: true,
            cancelable: true,
            view: window,
            clientX: rect.left + rect.width / 2,
            clientY: rect.top + rect.height / 2,
          })
        )
      );

      await collectVisibleProductsWithMid(rowIdx);
      await delay(300);
    }

    window.__parsedData__ = window.__productList;
    console.table(window.__parsedData__);
  }

  // 예시: 5번째, 6번째 중분류만 자동 수집
  await autoClickMidRange(4, 5);
})();
