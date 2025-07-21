(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  async function clickByExactId(id, label = "") {
    const el = document.getElementById(id);
    if (!el || el.offsetParent === null) {
      console.warn(`ID 클릭 실패: ${id}`);
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

    console.log(`클릭 완료${label ? " → " + label : ""}: ${id}`);
    return true;
  }

  async function closePopups() {
    const popupIds = [
        'mainframe.HFrameSet00.VFrameSet00.FrameSet.WorkFrame.STZZ120_P0.form.btn_close',
        'mainframe.HFrameSet00.VFrameSet00.FrameSet.WorkFrame.STZZ120_P0.form.btn_closeTop',
        'mainframe.HFrameSet00.VFrameSet00.TopFrame.STZZ210_P0.form.btn_enter'
    ];
    for (const id of popupIds) {
        const el = document.getElementById(id);
        if (el && el.offsetParent !== null) {
            await clickByExactId(id, "팝업 닫기");
            await delay(500);
        }
    }
  }

  async function pollAndClickMidFirstRow() {
    let attempts = 0;
    const maxAttempts = 30;

    const tryClick = async () => {
      const el = document.querySelector("div[id$='gdList.body.gridrow_0.cell_0_0']");
      if (!el || el.offsetParent === null) {
        if (++attempts < maxAttempts) return setTimeout(tryClick, 200);
        console.warn("중분류 첫행 셀 클릭 실패 (셀 없음)");
        return;
      }

      await clickByExactId(el.id, "중분류 첫행");
    };

    await tryClick();
  }

  async function goToMidMixRatio() {
    console.log("goToMidMixRatio 시작");
    await closePopups();

    // 1. 매출분석 탭 클릭
    const topMenuId = "mainframe.HFrameSet00.VFrameSet00.TopFrame.form.div_topMenu.form.STMB000_M0:icontext";
    await clickByExactId(topMenuId, "매출분석");
    await delay(2000);
    await closePopups();

    // 2. 중분류별 매출 구성비 메뉴 클릭
    const subMenuId = "mainframe.HFrameSet00.VFrameSet00.TopFrame.form.pdiv_topMenu_STMB000_M0.form.STMB011_M0:text";
    await clickByExactId(subMenuId, "중분류별 매출 구성비");
    await delay(3000);
    await closePopups();

    // 3. 중분류 리스트 첫행 클릭
    await pollAndClickMidFirstRow();
  }

  // 엔트리 포인트
  goToMidMixRatio();
})();