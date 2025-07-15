(() => {
  window.__liveData__ = window.__liveData__ || [];
  const seen = new Set(window.__liveData__);

  function getText(row, col) {
    const el = document.querySelector(
      `div[id*='gdDetail.body'][id*='cell_${row}_${col}'][id$=':text']`
    );
    return el?.innerText?.trim() || '';
  }

  function collectLines() {
    const rows = [
      ...document.querySelectorAll(
        "div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']"
      )
    ];
    const lines = [];
    for (const el of rows) {
      const row = el.id.match(/cell_(\d+)_0:text/)?.[1];
      if (!row) continue;
      const line = [
        getText(row, 0),
        getText(row, 1),
        getText(row, 2),
        getText(row, 3),
        getText(row, 4),
        getText(row, 5),
        getText(row, 6)
      ].join('\t');
      if (!seen.has(line)) {
        seen.add(line);
        lines.push(line);
      }
    }
    if (lines.length) {
      window.__liveData__.push(...lines);
      console.log(`📥 listener added ${lines.length} lines`);
    }
  }

  document.addEventListener('mid-clicked', () => setTimeout(collectLines, 100));
  document.addEventListener('product-scroll', () => setTimeout(collectLines, 100));
})();
