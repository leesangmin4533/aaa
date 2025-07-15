(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

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

  /**
   * 현재 선택된 중분류 행과 화면에 표시된 상품 행들을 읽어
   * window.__productList 배열에 누적 저장한다.
   */
  function collectVisibleProducts() {
    const list = (window.__productList = window.__productList || []);

    const midCodeCell = document.querySelector(
      "div[id*='gdList.body'][id*='cell_'][id$='_0:text'].nexagridcellfocused, " +
        "div[id*='gdList.body'][id*='cell_'][id$='_0:text'].nexagridselected"
    );
    const midCode = midCodeCell?.innerText?.trim() || '';

    let midText = '';
    if (midCodeCell) {
      const nameId = midCodeCell.id.replace('_0:text', '_1:text');
      const nameEl = document.getElementById(nameId);
      midText = nameEl?.innerText?.trim() || '';
    }

    const rows = [
      ...document.querySelectorAll(
        "div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']"
      ),
    ];

    for (const codeEl of rows) {
      const rowIndexMatch = codeEl.id.match(/cell_(\d+)_0:text$/);
      if (!rowIndexMatch) continue;
      const rowIdx = rowIndexMatch[1];

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

  async function collectAllProducts() {
    const list = (window.__productList = window.__productList || []);
    const seen = new Set(list.map(row => row.productCode));
    let scrollCount = 0;

    while (true) {
      const rows = [
        ...document.querySelectorAll(
          "div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']"
        ),
      ];

      let newCount = 0;
      const midCell = document.querySelector(
        "div[id*='gdList.body'][id*='cell_'][id$='_0:text'].nexagridcellfocused, " +
          "div[id*='gdList.body'][id*='cell_'][id$='_0:text'].nexagridselected"
      );
      const midCode = midCell?.innerText?.trim() || '';
      let midText = '';
      if (midCell) {
        const nameId = midCell.id.replace('_0:text', '_1:text');
        const nameEl = document.getElementById(nameId);
        midText = nameEl?.innerText?.trim() || '';
      }

      for (const codeEl of rows) {
        const match = codeEl.id.match(/cell_(\d+)_0:text$/);
        if (!match) continue;
        const rowIdx = match[1];

        const code = codeEl.innerText?.trim();
        if (!/^\d{13}$/.test(code)) continue;
        if (seen.has(code)) continue;

        const getText = col =>
          document.querySelector(
            `div[id*='gdDetail.body'][id*='cell_${rowIdx}_${col}:text']`
          )?.innerText?.trim() || '';

        list.push({
          midCode,
          midText,
          productCode: code,
          productName: getText(1),
          sales: getText(2),
          order: getText(3),
          purchase: getText(4),
          discard: getText(5),
          stock: getText(6),
        });
        seen.add(code);
        newCount++;
      }

      if (newCount === 0) break;

      const scrollBtn = document.querySelector(
        "div[id$='gdDetail.vscrollbar.incbutton:icontext']"
      );
      if (!scrollBtn) break;

      await clickElementById(scrollBtn.id);
      scrollCount++;
      console.log(`🔄 상품 스크롤 ${scrollCount}회`);
      await delay(1000);
    }

    console.log(`🎉 상품 ${seen.size}건 수집 완료`);
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

        seenMid.add(code);
        newMids.push(code);
        console.log(`✅ 중분류 클릭 완료: ${code}`);
        await delay(500);

        await collectAllProducts();
        await delay(300);
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
    // Python 측에서 읽을 수 있도록 전역 변수에 저장한다
    window.__parsedData__ = window.__productList;
  }

  autoClickAllMidCodesAndProducts();
})();
