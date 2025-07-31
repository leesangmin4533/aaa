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

    try {
        form.div_workForm.form.div2.form.div_search.form.calFromDay.set_value(dateStr);
        console.log(`[SET] calFromDay 값 → ${dateStr}`);
    } catch (e) {
        console.warn("[WARN] 날짜 설정 실패: " + e.message);
    }

    try {
        form.div_cmmbtn.form.F_10.click();
        console.log("[ACTION] 조회 버튼(F_10) 클릭");
    } catch (e) {
        console.warn("[WARN] 조회 버튼 클릭 실패: " + e.message);
    }
  };
})();
