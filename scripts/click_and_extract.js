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

  async function autoClickAllProductCodes() {
    const seen = new Set();
    let scrollCount = 0;

    while (true) {
      const textCells = [...document.querySelectorAll("div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']")];
      const newCodes = [];

      for (const textEl of textCells) {
        const code = textEl.innerText?.trim();
        if (!/^\d{13}$/.test(code)) continue;
        if (seen.has(code)) continue;

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

        seenMid.add(code);
        newMids.push(code);
        console.log(`✅ 중분류 클릭 완료: ${code}`);
        await delay(500);

        await autoClickAllProductCodes();
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
  }

  autoClickAllMidCodesAndProducts();
})();
