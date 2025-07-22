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
        console.log(`[waitForElement] Success! Element found: ${selector}`);
        return el;
      }
      await delay(300);
    }
    console.error(`[waitForElement] Timeout! Element not found or not visible: "${selector}"`);
    throw new Error(`Timeout: Element not found or not visible - ${selector}`);
  }

  // Improved function to wait for and retrieve a specific Nexacro component by its ID
  async function getFormComponent(componentId, timeout = 120000) {
    console.log(`[getFormComponent] Waiting for component: "${componentId}" (Timeout: ${timeout}ms)`);
    const start = Date.now();
    while (Date.now() - start < timeout) {
      try {
        const app = window.nexacro.getApplication();
        // Path to the main form, which can be adjusted if needed
        const mainForm = app?.mainframe?.HFrameSet00?.VFrameSet00?.FrameSet?.STMB011_M0?.form;
        if (mainForm && typeof mainForm.lookup === 'function') {
          const component = mainForm.lookup(componentId);
          if (component) {
            console.log(`[getFormComponent] Success! Found component: "${componentId}"`);
            return component;
          }
        }
      } catch (e) {
        // Ignore errors during polling, as the form might not be ready yet
      }
      await delay(300);
    }
    console.error(`[getFormComponent] Timeout! Component not found: "${componentId}"`);
    throw new Error(`Timeout: Nexacro component not found - ${componentId}`);
  }

  // Refactored to use the robust getFormComponent function
  async function inputDateAndSearch(dateStr) {
    console.log(`[inputDateAndSearch] Starting process for date: ${dateStr}`);
    try {
      // More robustly get components by their ID
      const dateInput = await getFormComponent("calFromDay");
      const searchBtn = await getFormComponent("F_10"); // Assumes "F_10" is the unique ID for the search button

      console.log(`[inputDateAndSearch] Attempting to set date value to "${dateStr}" using nexacro API.`);
      dateInput.set_value(dateStr);
      await delay(100);
      console.log(`[inputDateAndSearch] Successfully set date value. Current value: "${dateInput.value}"`);

      if (!searchBtn || typeof searchBtn.click !== 'function') {
        const errorMsg = "Search button (F_10) component not found or is not clickable.";
        console.error(`[inputDateAndSearch] ${errorMsg}`);
        throw new Error(errorMsg);
      }

      console.log("[inputDateAndSearch] Search button component found. Attempting to click...");
      searchBtn.click();
      console.log(`[inputDateAndSearch] Click command issued for search button.`);

      // Wait for search results to appear in the DOM
      await waitForElement("div[id*='gdList.body'][id$='0_0:text']", 15000);
      console.log(`[inputDateAndSearch] Result grid loaded for date: ${dateStr}.`);

    } catch (err) {
      const errorMessage = `[${dateStr}] 처리 실패: ${err.message}`;
      window.automation.error = errorMessage;
      console.error(`[inputDateAndSearch] Error during process for date ${dateStr}:`, err);
      throw err;
    }
  }

  // Refactored to be more streamlined
  async function collectSingleDayData(dateStr) {
    console.log(`[collectSingleDayData] Starting collection for date: ${dateStr}`);
    try {
      window.automation.error = null;
      window.automation.parsedData = null;

      console.log(`[collectSingleDayData] Calling inputDateAndSearch for date: ${dateStr}`);
      await inputDateAndSearch(dateStr);
      console.log(`[collectSingleDayData] inputDateAndSearch completed for date: ${dateStr}`);

      // Assuming 'autoClickAllMidCodesAndProducts' is loaded and available
      console.log("[collectSingleDayData] Executing 'autoClickAllMidCodesAndProducts'...");
      await window.automation.autoClickAllMidCodesAndProducts();
      console.log("[collectSingleDayData] Finished executing 'autoClickAllMidCodesAndProducts'.");

      if (window.automation.parsedData) {
        console.log(`[collectSingleDayData] Successfully collected data for ${dateStr}. Data length: ${window.automation.parsedData.length}`);
        return { success: true, data: window.automation.parsedData };
      } else {
        const msg = `No data collected for date ${dateStr}.`;
        console.warn(`[collectSingleDayData] ${msg}`);
        return { success: true, data: [], message: msg };
      }
    } catch (err) {
      const errorMessage = `Error during single day collection for ${dateStr}: ${err.message}`;
      console.error(`[collectSingleDayData] ${errorMessage}`, err);
      window.automation.error = errorMessage;
      return { success: false, message: errorMessage };
    }
  }

  // Expose the primary function for external calls
  window.automation.collectSingleDayData = collectSingleDayData;
  console.log("Single Day Collector script updated. Call `window.automation.collectSingleDayData(dateStr)` to start.");

})();