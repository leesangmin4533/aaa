(() => {
  /**
   * 지정된 날짜로 calFromDay 컴포넌트의 값을 설정하고 조회 버튼을 클릭합니다.
   * @param {string} dateStr - YYYYMMDD 형식의 날짜 문자열 (예: "20250720")
   */
  window.automation.changeDateAndSearch = (dateStr) => {
    const app = window.nexacro.getApplication();
    if (!app) {
      console.error("Nexacro Application 객체를 찾을 수 없습니다.");
      return;
    }

    const form = app.mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form;
    if (!form) {
      console.error("메인 폼(STMB011_M0)을 찾을 수 없습니다.");
      return;
    }

    const calFromDay = form.div_workForm.form.div2.form.div_search.form.calFromDay;
    if (calFromDay) {
      calFromDay.set_value(dateStr);
      console.log(`[SET] calFromDay 값 → ${dateStr}`);
    } else {
      console.warn("[WARN] calFromDay 컴포넌트를 찾을 수 없습니다.");
    }

    const searchBtn = form.div_cmmbtn.form.F_10;
    if (searchBtn) {
      // waitForTransaction은 nexacro_automation_library.js에 정의되어 있으므로 직접 호출
      // Promise를 반환하므로 Python에서 await 처리 필요
      window.automation.waitForTransaction('search'); 
      searchBtn.click();
      console.log("[ACTION] 조회 버튼(F_10) 클릭");
    } else {
      console.warn("[WARN] 조회 버튼(F_10)을 찾을 수 없습니다.");
    }
  };
})();