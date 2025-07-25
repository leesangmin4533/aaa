(async () => {
  const form = app.mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form;
  const dsList = form.div_workForm.form.dsList;
  const gdList = form.div_workForm.form.div2.form.gdList;
  const result = [];

  const delay = ms => new Promise(res => setTimeout(res, ms));

  for (let i = 0; i < dsList.getRowCount(); i++) {
    const midCode = dsList.getColumn(i, "MID_CD");
    const midName = dsList.getColumn(i, "MID_NM");

    gdList.selectRow(i);
    const evt = new nexacro.GridClickEventInfo(gdList, "oncellclick", false, false, false, false, 0, 0, i, i);
    gdList.oncellclick && gdList.oncellclick._fireEvent(gdList, evt);

    console.log(`▶ 중분류 [${midCode}] 클릭`);
    
    // 상품 목록 로딩을 위한 트랜잭션 완료까지 대기 (가장 중요!)
    await window.automation.waitForTransaction("searchDetail");

    const dsDetail = form.div_workForm.form.dsDetail;
    const items = [];
    for (let j = 0; j < dsDetail.getRowCount(); j++) {
      items.push({
        midCode:     midCode,
        midName:     midName,
        productCode: dsDetail.getColumn(j, "ITEM_CD"),
        productName: dsDetail.getColumn(j, "ITEM_NM"),
        sales:       dsDetail.getColumn(j, "SALE_QTY"),
        order_cnt:   dsDetail.getColumn(j, "ORD_QTY"),
        purchase:    dsDetail.getColumn(j, "BUY_QTY"),
        disposal:    dsDetail.getColumn(j, "DISUSE_QTY"),
        stock:       dsDetail.getColumn(j, "STOCK_QTY")
      });
    }

    result.push(...items);
    console.log(`✅ ${midName} - ${items.length}개 상품 수집 완료`);
    await delay(300);
  }

  window.__중분류상품수집결과__ = result;
  console.log(" 전체 수집 완료:", result);
})();
