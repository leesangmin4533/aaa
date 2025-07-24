(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  async function findElementByNexacroId(id) {
    try {
      // Nexacro ID를 점으로 분할하여 각 부분을 처리
      const parts = id.split('.');
      const finalPart = parts[parts.length - 1].split(':')[0];
      
      // 다양한 선택자 조합을 시도
      const selectors = [
        `[id$="${finalPart}"]`,                    // ID 끝부분으로 찾기
        `[id*="${finalPart}"]`,                    // ID 일부로 찾기
        `[id*="${parts[parts.length - 2]}"]`       // 상위 컴포넌트 ID로 찾기
      ];

      for (const selector of selectors) {
        const elements = document.querySelectorAll(selector);
        for (const el of elements) {
          if (el.offsetParent !== null) {  // 화면에 보이는 요소만 선택
            return el;
          }
        }
      }
      return null;
    } catch (e) {
      console.error(`요소 검색 중 오류 발생: ${e}`);
      return null;
    }
  }

  async function clickByExactId(id, label = "") {
    console.log(`🔍 요소 검색 중: ${id} ${label ? `(${label})` : ""}`);
    
    const el = await findElementByNexacroId(id);
    if (!el || el.offsetParent === null) {
      console.warn(`⛔ 클릭 실패: ${id} ${label ? `(${label})` : ""}`);
      return false;
    }

    try {
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
      
      console.log(`✅ 클릭 성공: ${id} ${label ? `(${label})` : ""}`);
      return true;
    } catch (e) {
      console.error(`클릭 이벤트 발생 중 오류: ${e}`);
      return false;
    }
  }

  (async () => {
    try {
      // 1. 매출분석 탭 클릭
      console.log("🔍 매출분석 메뉴 진입 시도...");
      const topMenuId = "mainframe.HFrameSet00.VFrameSet00.TopFrame.form.div_topMenu.form.STMB000_M0:icontext";
      const ok1 = await clickByExactId(topMenuId, "매출분석");
      if (!ok1) {
        console.error("❌ 매출분석 메뉴 클릭 실패");
        return;
      }
      
      // 메뉴 표시를 위한 대기
      console.log("⏳ 서브메뉴 로딩 대기 중...");
      await delay(2000);

      // 2. 중분류별 매출 구성비 클릭
      const subMenuId = "mainframe.HFrameSet00.VFrameSet00.TopFrame.form.pdiv_topMenu_STMB000_M0.form.STMB011_M0:text";
      console.log("🔍 중분류별 매출 구성비 메뉴 진입 시도...");
      const ok2 = await clickByExactId(subMenuId, "중분류별 매출 구성비");
      if (!ok2) {
        console.error("❌ 중분류별 매출 구성비 메뉴 클릭 실패");
        return;
      }

      // 페이지 로딩 대기
      console.log("⏳ 페이지 로딩 대기 중...");
      await delay(2000);
      
      // 로딩 완료 표시
      console.log("✅ 네비게이션 완료");
    } catch (e) {
      console.error(`네비게이션 중 오류 발생: ${e}`);
    }
  })();
})();
