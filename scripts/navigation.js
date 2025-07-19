(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  async function clickByExactId(id, label = "") {
    const el = document.getElementById(id);
    if (!el || el.offsetParent === null) {
      console.warn(`⛔ ID 클릭 실패: ${id}`);
      return false;
    }

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

    console.log(`✅ 클릭 완료${label ? " → " + label : ""}: ${id}`);
    return true;
  }

  async function pollAndClickMidFirstRow() {
    let attempts = 0;
    const maxAttempts = 30;

    const tryClick = () => {
      const el = document.querySelector("div[id$='gdList.body.gridrow_0.cell_0_0']");
      if (!el || el.offsetParent === null) {
        if (++attempts < maxAttempts) return setTimeout(tryClick, 200);
        console.warn("⛔ 중분류 첫행 셀 클릭 실패 (셀 없음)");
        return;
      }

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
      console.log(`✅ 중분류 첫행 클릭 완료 → ID: ${el.id}`);
    };

    tryClick();
  }

  async function goToMidMixRatio() {
    console.log("🚀 goToMidMixRatio 시작");
    // 1. 매출분석 탭 클릭
    const topMenuId = "mainframe.HFrameSet00.VFrameSet00.TopFrame.form.div_topMenu.form.STMB000_M0:icontext";
    console.log(`Attempting to click top menu: ${topMenuId}`);
    const ok1 = await clickByExactId(topMenuId, "매출분석");
    if (!ok1) {
      console.error("❌ 매출분석 탭 클릭 실패");
      return;
    }
    console.log("✅ 매출분석 탭 클릭 성공");
    await delay(2000);

    // 2. 중분류별 매출 구성비 메뉴 클릭
    const subMenuId = "mainframe.HFrameSet00.VFrameSet00.TopFrame.form.pdiv_topMenu_STMB000_M0.form.STMB011_M0:text";
    console.log(`Attempting to click sub menu: ${subMenuId}`);
    const ok2 = await clickByExactId(subMenuId, "중분류별 매출 구성비");
    if (!ok2) {
      console.error("❌ 중분류별 매출 구성비 메뉴 클릭 실패");
      return;
    }
    console.log("✅ 중분류별 매출 구성비 메뉴 클릭 성공");
    await delay(3000);

    // 3. 중분류 리스트 첫행 클릭
    console.log("Attempting to click first row of mid-category list.");
    await pollAndClickMidFirstRow();
    console.log("✅ 중분류 리스트 첫행 클릭 시도 완료");
  }

  // ✅ 엔트리 포인트
  goToMidMixRatio();
})();
