(() => {
  function parseDetailDataset(dsDetail, midCode, midName) {
    const products = [];
    if (!dsDetail) return products;
    for (let i = 0; i < dsDetail.getRowCount(); i++) {
      products.push({
        midCode,
        midName,
        productCode: dsDetail.getColumn(i, 'ITEM_CD'),
        productName: dsDetail.getColumn(i, 'ITEM_NM'),
        sales: parseInt(dsDetail.getColumn(i, 'SALE_QTY') || 0, 10),
        order_cnt: parseInt(dsDetail.getColumn(i, 'ORD_QTY') || 0, 10),
        purchase: parseInt(dsDetail.getColumn(i, 'BUY_QTY') || 0, 10),
        disposal: parseInt(dsDetail.getColumn(i, 'DISUSE_QTY') || 0, 10),
        stock: parseInt(dsDetail.getColumn(i, 'STOCK_QTY') || 0, 10),
      });
    }
    return products;
  }

  function parseListDataset(dsList) {
    const mids = [];
    if (!dsList) return mids;
    for (let i = 0; i < dsList.getRowCount(); i++) {
      mids.push({
        code: dsList.getColumn(i, 'MID_CD'),
        name: dsList.getColumn(i, 'MID_NM'),
        expectedQuantity: parseInt(dsList.getColumn(i, 'SALE_QTY') || 0, 10),
        row: i,
      });
    }
    return mids;
  }

  window.automationHelpers = window.automationHelpers || {};
  Object.assign(window.automationHelpers, {
    parseDetailDataset,
    parseListDataset,
  });
})();
