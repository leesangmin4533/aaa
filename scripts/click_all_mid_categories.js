(() => {
  const logs = [];
  const targetCode = window.__targetMidCode__ || null;

  const getCells = () =>
    [...document.querySelectorAll(
      "div[id*='gdList.body'][id*='cell_'][id$='_0:text']"
    )];

  const clickEl = el => {
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
  };

  const processCell = cell => {
    const code = cell.innerText.trim();
    const el = document.getElementById(cell.id.replace(":text", ""));
    if (!el) {
      logs.push({ code, status: "not-found" });
      console.warn("⛔ 클릭 대상 없음:", code);
      return;
    }
    clickEl(el);
    logs.push({ code, status: "success" });
    console.log(`✅ 클릭 완료: 중분류 코드 ${code}`);
  };

  if (targetCode) {
    const cell = getCells().find(el => el.innerText?.trim() === targetCode);
    if (!cell) {
      console.warn("⛔ 중분류 코드 셀 찾을 수 없음:", targetCode);
      logs.push({ code: targetCode, status: "not-found" });
    } else {
      processCell(cell);
    }
  } else {
    getCells().forEach(processCell);
  }

  window.__midCategoryLogs__ = logs;
  console.log("mid category click logs", logs);
})();
