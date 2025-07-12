(() => {
  const parseNumber = (cell) => {
    if (!cell) return 0;
    const txt = cell.innerText.replace(/,/g, '').trim();
    return txt === '' ? 0 : Number(txt);
  };

  const rows = [];
  for (let i = 0; ; i++) {
    const codeCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${i}_0'][id$=':text']`);
    if (!codeCell) break;
    const nameCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${i}_1'][id$=':text']`);
    const salesCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${i}_2'][id$=':text']`);
    const orderCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${i}_3'][id$=':text']`);
    const purchaseCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${i}_4'][id$=':text']`);
    const discardCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${i}_5'][id$=':text']`);
    const stockCell = document.querySelector(`div[id*='gdDetail.body'][id*='cell_${i}_6'][id$=':text']`);
    rows.push({
      code: codeCell.innerText.trim(),
      name: nameCell ? nameCell.innerText.trim() : '',
      sales: parseNumber(salesCell),
      order: parseNumber(orderCell),
      purchase: parseNumber(purchaseCell),
      discard: parseNumber(discardCell),
      stock: parseNumber(stockCell)
    });
  }
  window.__parsedData__ = rows;
})();
