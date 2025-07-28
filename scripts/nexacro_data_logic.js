(() => {
  // Nexacro 핵심 헬퍼 함수들을 window.automation에서 가져옵니다.
  const getMainForm = window.automation.getMainForm;

  async function collectProductsFromDataset(midCode, midName, scope) {
    const products = [];
    const dsDetail = getMainForm()?.div_workForm?.form?.dsDetail;

    if (!dsDetail) {
      console.warn("[collectProductsFromDataset] dsDetail 데이터셋을 찾을 수 없습니다.");
      return products;
    }

    for (let i = 0; i < dsDetail.getRowCount(); i++) {
      products.push({
        midCode:     midCode,
        midName:     midName,
        productCode: dsDetail.getColumn(i, "ITEM_CD"),
        productName: dsDetail.getColumn(i, "ITEM_NM"),
        sales:       parseInt(dsDetail.getColumn(i, "SALE_QTY") || 0, 10),
        order_cnt:   parseInt(dsDetail.getColumn(i, "ORD_QTY") || 0, 10),
        purchase:    parseInt(dsDetail.getColumn(i, "BUY_QTY") || 0, 10),
        disposal:    parseInt(dsDetail.getColumn(i, "DISUSE_QTY") || 0, 10),
        stock:       parseInt(dsDetail.getColumn(i, "STOCK_QTY") || 0, 10),
      });
    }
    console.log(`[collectProductsFromDataset] '${midName}'의 상품 ${products.length}개를 데이터셋에서 수집합니다.`);
    return products;
  }

  async function getAllMidCodesFromDataset(scope) {
    const midCodes = [];
    const dsList = getMainForm()?.div_workForm?.form?.dsList;

    if (!dsList) {
      console.warn("[getAllMidCodesFromDataset] dsList 데이터셋을 찾을 수 없습니다.");
      return midCodes;
    }

    for (let i = 0; i < dsList.getRowCount(); i++) {
      const code = dsList.getColumn(i, "MID_CD");
      const name = dsList.getColumn(i, "MID_NM");

      midCodes.push({
        code:             code,
        name:             name,
        expectedQuantity: parseInt(dsList.getColumn(i, "SALE_QTY") || 0, 10),
        row:              i,
      });
    }
    console.log(`[getAllMidCodesFromDataset] ${midCodes.length}개의 중분류를 데이터셋에서 찾았습니다.`);
    return midCodes;
  }

  // window.automation 객체에 데이터 로직 함수들 노출
  Object.assign(window.automation, {
    collectProductsFromDataset,
    getAllMidCodesFromDataset,
  });
})();