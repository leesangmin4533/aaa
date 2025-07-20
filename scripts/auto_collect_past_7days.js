(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  if (!window.automation) window.automation = {};
  window.automation.error = null;

  // ✅ wait until a DOM element matching selector exists
  async function waitForElement(selector, timeout = 5000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const el = document.querySelector(selector);
      if (el && el.offsetParent !== null) return el;
      await delay(300);
    }
    throw new Error(`Timeout: Element not found - ${selector}`);
  }

  function getPastDates(n = 7) {
    const dates = [];
    const today = new Date();
    for (let i = 1; i <= n; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      const str = d.toISOString().split("T")[0];
      dates.push(str);
    }
    return dates;
  }

  function clickByElement(el) {
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

  async function inputDateAndSearch(dateStr) {
    try {
      // ✅ Nexacro API 기반 날짜 설정
      const app = window.nexacro.getApplication();
      app.mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form
        .div_workForm.form.div_search.form.calFromDay.set_value(dateStr);
      await delay(300);

      // ✅ 조회 버튼 클릭
      const searchBtnId = "mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_cmmbtn.form.F_10";
      const searchBtn = await waitForElement(`#${CSS.escape(searchBtnId)}`);
      clickByElement(searchBtn);
      console.log(` 조회 실행 - 날짜: ${dateStr}`);
      await delay(1500);

      // ✅ 결과 대기 (gdList 렌더링 기준)
      await waitForElement("div[id*='gdList.body'][id$='0_0:text']");
    } catch (err) {
      window.automation.error = `❌ [${dateStr}] 처리 실패: ${err.message}`;
      throw err;
    }
  }

  async function collectPast7Days() {
    try {
      window.automation.error = null;
      const dates = getPastDates(7);
      for (const date of dates) {
        await inputDateAndSearch(date);
        if (typeof window.automation.autoClickAllMidCodesAndProducts === "function") {
          await window.automation.autoClickAllMidCodesAndProducts();
        } else {
          throw new Error("통합 수집 함수(autoClickAllMidCodesAndProducts)가 정의되지 않았습니다.");
        }
        await delay(1000);
      }
      console.log("✅ 과거 7일치 수집 완료");
    } catch (err) {
      console.error("⛔ collectPast7Days 실패:", err);
    }
  }

  //  호출 메서드 등록
  window.automation.collectPast7Days = collectPast7Days;
})();