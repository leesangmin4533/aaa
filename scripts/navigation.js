(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  async function clickByExactId(id, label = "") {
    const el = document.getElementById(id);
    if (!el || el.offsetParent === null) {
      console.warn(`ID 클릭 실패: ${id}`);
      return false;
    }

    // 요소가 클릭 가능한 상태가 될 때까지 대기
    await delay(10000);  // 기본 10초 대기

    // Nexacro 컴포넌트의 click() 메서드를 우선적으로 시도
    if (typeof el.click === 'function') {
      el.click();
    } else {
      // 일반 DOM 요소인 경우 MouseEvent 디스패치
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
    }
    
    // 클릭 후 데이터 로드 대기
    console.log(`클릭 이벤트 발생 ${label ? " → " + label : ""}: ${id}`);
    await delay(10000);  // 데이터 로드를 위한 10초 대기

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
            await delay(10000);
        }
    }
  }

  function triggerGridRowClick(rowIndex = 0) {
    const f = window.nexacro.getApplication().mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form;
    const gList = f?.div_workForm?.form?.div2?.form?.gdList;
    if (!gList || typeof gList.selectRow !== "function") {
      console.warn("⚠️ gdList 초기화 안됨");
      return;
    }

    gList.selectRow(rowIndex);
    const evt = new nexacro.GridClickEventInfo(
      gList, "oncellclick", false, false, false, false, 0, 0, rowIndex, rowIndex
    );

    console.log("✅ Nexacro oncellclick 강제 발생");
    gList.oncellclick._fireEvent(gList, evt);
  }

  async function pollAndClickMidFirstRow() {
    const maxAttempts = 30;
    let attempts = 0;

    const tryClick = () => {
      const f = window.nexacro.getApplication().mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form;
      const gList = f?.div_workForm?.form?.div2?.form?.gdList;
      if (gList && typeof gList.selectRow === "function") {
        triggerGridRowClick(0);
      } else {
        if (++attempts < maxAttempts) {
          setTimeout(tryClick, 300);
        } else {
          console.warn("⚠️ gdList 초기화 실패");
        }
      }
    };

    tryClick();
  }

  async function goToMidMixRatio() {
    console.log("goToMidMixRatio 시작");
    await closePopups();

    // 1. 매출분석 탭 클릭
    const topMenuId = "mainframe.HFrameSet00.VFrameSet00.TopFrame.form.div_topMenu.form.STMB000_M0:icontext";
    await clickByExactId(topMenuId, "매출분석");
    await delay(10000);
    await closePopups();

    // 2. 중분류별 매출 구성비 메뉴 클릭
    const subMenuId = "mainframe.HFrameSet00.VFrameSet00.TopFrame.form.pdiv_topMenu_STMB000_M0.form.STMB011_M0:text";
    await clickByExactId(subMenuId, "중분류별 매출 구성비");
    await delay(10000);
    await closePopups();

    // 3. 중분류 리스트 첫행 클릭
    await pollAndClickMidFirstRow();
  }

  // 엔트리 포인트
  goToMidMixRatio();
})();
