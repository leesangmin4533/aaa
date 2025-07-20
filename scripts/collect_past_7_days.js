(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  if (!window.automation) window.automation = {};
  window.automation.error = null;

  async function waitForElement(selector, timeout = 5000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const el = document.querySelector(selector);
      if (
        el &&
        el.offsetParent !== null &&
        window.getComputedStyle(el).display !== 'none' &&
        window.getComputedStyle(el).visibility !== 'hidden'
      ) {
        return el;
      }
      await delay(300);
    }
    throw new Error(`Timeout: Element not fully visible - ${selector}`);
  }

  function getPastDates(n = 7) {
    const dates = [];
    const today = new Date();
    for (let i = 1; i <= n; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      dates.push(d.toISOString().split("T")[0]);
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
      const app = window.nexacro.getApplication();
      app.mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form
        .div_workForm.form.div_search.form.calFromDay.set_value(dateStr);
      await delay(300);

      const searchBtn = await waitForElement("div[id$='F_10:icontext']");
      clickByElement(searchBtn);
      console.log(`🔍 조회 실행 - 날짜: ${dateStr}`);
      await delay(1500);

      // 데이터 존재 확인: 최소한 첫 셀이 렌더링되어야 함
      await waitForElement("div[id*='gdList.body'][id*='cell_'][id$='_0:text']");
    } catch (err) {
      const msg = `❌ 날짜 ${dateStr} 처리 실패: ${err.message}`;
      console.error(msg);
      window.automation.error = msg;
      throw err;
    }
  }

  async function collectPast7Days() {
    return new Promise(async (resolve, reject) => {
      try {
        window.automation.error = null;
        const dates = getPastDates(7);

        for (const date of dates) {
          await inputDateAndSearch(date);

          if (typeof window.automation.autoClickAllMidCodesAndProducts === "function") {
            await window.automation.autoClickAllMidCodesAndProducts();
          } else {
            throw new Error("❌ 수집 함수(autoClickAllMidCodesAndProducts)가 로드되지 않았습니다.");
          }

          await delay(1000);
        }

        console.log("✅ 과거 7일치 수집 완료");
        resolve("✅ 완료");
      } catch (err) {
        const finalMsg = `⛔ collectPast7Days 실패: ${err.message}`;
        console.error(finalMsg);
        window.automation.error = finalMsg;
        reject(err);
      }
    });
  }

  window.automation.collectPast7Days = collectPast7Days;
})();
