(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  if (!window.automation) window.automation = {};
  window.automation.error = null;

  async function waitForElement(selector, timeout = 10000) {
    console.log(`[waitForElement] Waiting for selector: "${selector}" (Timeout: ${timeout}ms)`);
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const el = document.querySelector(selector);
      if (el && el.offsetParent !== null) {
        console.log(`[waitForElement] ✅ Success! Element found: "${selector}"`);
        return el;
      }
      await delay(300);
    }
    console.error(`[waitForElement] ⛔ Timeout! Element not found or not visible: "${selector}"`);
    throw new Error(`Timeout: Element not found or not visible - ${selector}`);
  }

  async function waitForFullForm(timeout = 10000) {
    console.log(`[waitForFullForm] Waiting for Nexacro form to be ready... (Timeout: ${timeout}ms)`);
    const start = Date.now();
    while (Date.now() - start < timeout) {
      try {
        const app = window.nexacro.getApplication();
        const form = app?.mainframe?.HFrameSet00?.VFrameSet00?.FrameSet?.STMB011_M0?.form;
        const search = form?.div_workForm?.form?.div_search?.form;
        if (search?.calFromDay && typeof search.calFromDay.set_value === "function") {
          console.log("[waitForFullForm] ✅ Success! Nexacro form is ready.", search);
          return search;
        }
      } catch (e) {
        // Ignore errors during polling
      }
      await delay(300);
    }
    console.error("[waitForFullForm] ⛔ Timeout! Nexacro search form component (calFromDay) not ready.");
    throw new Error("Timeout: Nexacro search form component (calFromDay) not ready.");
  }

  function getPastDates(n = 7) {
    const dates = [];
    const today = new Date();
    for (let i = 1; i <= n; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() - i);
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      dates.push(`${year}${month}${day}`);
    }
    console.log(`[getPastDates] Generated dates for the past ${n} days:`, dates);
    return dates;
  }

  async function inputDateAndSearch(dateStr) {
    console.log(`[inputDateAndSearch] Starting process for date: ${dateStr}`);
    try {
      const searchForm = await waitForFullForm();

      console.log(`[inputDateAndSearch] Attempting to set date value to "${dateStr}" using nexacro API.`);
      searchForm.calFromDay.set_value(dateStr);
      await delay(100);
      console.log(`[inputDateAndSearch] Successfully set date value. Current value: "${searchForm.calFromDay.value}"`);

      const app = window.nexacro.getApplication();
      const mainForm = app.mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form;
      const searchBtn = mainForm.div_cmmbtn.form.F_10;

      if (!searchBtn || typeof searchBtn.click !== 'function') {
        console.error("[inputDateAndSearch] ⛔ Search button (F_10) component not found or is not clickable.", searchBtn);
        throw new Error("Search button (F_10) component not found or is not clickable.");
      }
      
      console.log("[inputDateAndSearch] Search button component found:", searchBtn);
      console.log(`[inputDateAndSearch] Attempting to click search button for date: ${dateStr}`);
      searchBtn.click();
      console.log(`[inputDateAndSearch] ✅ Click command issued for search button.`);

      await waitForElement("div[id*='gdList.body'][id$='0_0:text']", 15000);
      console.log(`[inputDateAndSearch] Result grid loaded for date: ${dateStr}.`);

    } catch (err) {
      const errorMessage = `❌ [${dateStr}] 처리 실패: ${err.message}`;
      window.automation.error = errorMessage;
      console.error(`[inputDateAndSearch] ⛔ Error during process for date ${dateStr}:`, err);
      throw err;
    }
  }

  async function collectPast7Days() {
    console.log("🚀 [collectPast7Days] Starting 7-day data collection process.");
    try {
      window.automation.error = null;
      const dates = getPastDates(7);

      for (const date of dates) {
        console.log(`-------------------- Processing Date: ${date} --------------------`);
        await inputDateAndSearch(date);
        
        console.log(`[collectPast7Days] Date ${date} processed. Checking for 'autoClickAllMidCodesAndProducts' function.`);
        if (typeof window.automation.autoClickAllMidCodesAndProducts === "function") {
          console.log("[collectPast7Days] Found 'autoClickAllMidCodesAndProducts'. Executing now...");
          await window.automation.autoClickAllMidCodesAndProducts();
          console.log("[collectPast7Days] ✅ Finished executing 'autoClickAllMidCodesAndProducts'.");
        } else {
          console.error("[collectPast7Days] ⛔ 'autoClickAllMidCodesAndProducts' function is not defined.");
          throw new Error("통합 수집 함수(autoClickAllMidCodesAndProducts)가 정의되지 않았습니다.");
        }
        await delay(1000);
      }
      console.log("🎉 [collectPast7Days] ✅ Successfully completed collection for all 7 days.");
    } catch (err) {
      console.error("⛔ [collectPast7Days] An error occurred during the 7-day collection process:", err.message);
    }
  }

  window.automation.collectPast7Days = collectPast7Days;
  console.log("📜 7-Day Collector script loaded with enhanced logging. Call `window.automation.collectPast7Days()` to start.");
})();
