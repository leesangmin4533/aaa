(() => {
  const rows = [];
  for (let i = 0; ; i++) {
    const codeCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${i}_0'][id$=':text']`);
    if (!codeCell) break;
    const nameCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${i}_1'][id$=':text']`);
    rows.push({
      code: codeCell.innerText.trim(),
      name: nameCell ? nameCell.innerText.trim() : ''
    });
  }
  window.__parsedData__ = rows;
})();
