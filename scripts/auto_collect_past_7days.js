(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  if (!window.automation) window.automation = {};
  window.automation.error = null;
  window.automation.logs = [];

  const origConsoleLog = console.log;
  console.log = function (...args) {
    window.automation.logs.push(args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg))).join(' '));
    return origConsoleLog.apply(console, args);
  };

  const origConsoleError = console.error;
  console.error = function (...args) {
    window.automation.logs.push("[ERROR] " + args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg))).join(' '));
    return origConsoleError.apply(console, args);
  };

  async function waitForElement(selector, timeout = 120000) {
    console.log(`[waitForElement] Waiting for selector: "${selector}" (Timeout: ${timeout}ms)`);
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const el = document.querySelector(selector);
      if (el && el.offsetParent !== null) {
        console.log("[waitForElement] Success! Element found: " + selector);
        return el;
      }
      await delay(300);
    }
    console.error(`[waitForElement] Timeout! Element not found or not visible: "${selector}"`);
    throw new Error(`Timeout: Element not found or not visible - ${selector}`);
  }

  async function waitForFullForm(timeout = 120000) {
    console.log(`[waitForFullForm] Waiting for Nexacro form to be ready with corrected path... (Timeout: ${timeout}ms)`);
    const start = Date.now();
    while (Date.now() - start < timeout) {
      try {
        const app = window.nexacro.getApplication();
        const form = app?.mainframe?.HFrameSet00?.VFrameSet00?.FrameSet?.STMB011_M0?.form;
        const search = form?.div_workForm?.form?.div2?.form?.div_search?.form;
        if (search?.calFromDay && typeof search.calFromDay.set_value === "function") {
          console.log("[waitForFullForm] Success! Nexacro form is ready with corrected path.");
          return search;
        }
      } catch (e) {
        // Ignore errors during polling
      }
      await delay(300);
    }
    console.error("[waitForFullForm] Timeout! Nexacro search form component (calFromDay) not ready even with corrected path.");
    throw new Error("Timeout: Nexacro search form component (calFromDay) not ready.");
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
        console.error("[inputDateAndSearch] Search button (F_10) component not found or is not clickable.");
        throw new Error("Search button (F_10) component not found or is not clickable.");
      }
      
      console.log("[inputDateAndSearch] Search button component found. Attempting to click...");
      searchBtn.click();
      console.log(`[inputDateAndSearch] Click command issued for search button.`);

      await waitForElement("div[id*='gdList.body'][id$='0_0:text']", 15000);
      console.log(`[inputDateAndSearch] Result grid loaded for date: ${dateStr}.`);

    } catch (err) {
      const errorMessage = `[${dateStr}] 처리 실패: ${err.message}`;
      window.automation.error = errorMessage;
      console.error(`[inputDateAndSearch] Error during process for date ${dateStr}:`, err);
      throw err;
    }
  }

  // New function to collect data for a single date
  async function collectSingleDayData(dateStr) {
    console.log(`[collectSingleDayData] Starting collection for date: ${dateStr}`);
    try {
      window.automation.error = null; // Reset error for this run
      window.automation.parsedData = null; // Reset parsedData for this run

      console.log(`[collectSingleDayData] Calling inputDateAndSearch for date: ${dateStr}`);
      await inputDateAndSearch(dateStr);
      console.log(`[collectSingleDayData] inputDateAndSearch completed for date: ${dateStr}`);
      
      console.log(`[collectSingleDayData] Date ${dateStr} processed. Checking for 'autoClickAllMidCodesAndProducts' function.`);
      if (typeof window.automation.autoClickAllMidCodesAndProducts === "function") {
        console.log("[collectSingleDayData] Found 'autoClickAllMidCodesAndProducts'. Executing now...");
        await window.automation.autoClickAllMidCodesAndProducts(); // This populates window.automation.parsedData
        console.log("[collectSingleDayData] Finished executing 'autoClickAllMidCodesAndProducts'.");
        
        if (window.automation.parsedData) {
          console.log(`[collectSingleDayData] Successfully collected data for ${dateStr}. Data length: ${window.automation.parsedData.length}`);
          return { success: true, data: window.automation.parsedData };
        } else {
          const msg = `No data collected for date ${dateStr}.`;
          console.warn(`[collectSingleDayData] ${msg}`);
          return { success: true, data: [], message: msg }; // Return success with empty data if no data
        }
      } else {
        const msg = "'autoClickAllMidCodesAndProducts' function is not defined.";
        console.error(`[collectSingleDayData] ${msg}`);
        window.automation.error = msg;
        return { success: false, message: msg };
      }
    } catch (err) {
      const errorMessage = `Error during single day collection for ${dateStr}: ${err.message}`;
      console.error(`[collectSingleDayData] ${errorMessage}`, err);
      window.automation.error = errorMessage;
      return { success: false, message: errorMessage };
    }
  }

  // Expose the new function
  window.automation.collectSingleDayData = collectSingleDayData;
  console.log("Single Day Collector script updated. Call `window.automation.collectSingleDayData(dateStr)` to start.");

})();
