(() => {
  // Helper function to introduce a delay
  const delay = ms => new Promise(res => setTimeout(res, ms));

  // Setup a namespace on the window object for automation scripts
  if (!window.automation) window.automation = {};
  window.automation.error = null;

  /**
   * Waits for a specified element to appear in the DOM and be visible.
   * @param {string} selector - The CSS selector for the element.
   * @param {number} [timeout=10000] - The maximum time to wait in milliseconds.
   * @returns {Promise<Element>} The found element.
   * @throws {Error} If the element is not found within the timeout period.
   */
  async function waitForElement(selector, timeout = 10000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const el = document.querySelector(selector);
      // Check if the element exists and is visible (has an offsetParent)
      if (el && el.offsetParent !== null) return el;
      await delay(300);
    }
    throw new Error(`Timeout: Element not found or not visible - ${selector}`);
  }

  /**
   * Waits for the main nexacro form and its components to be fully initialized.
   * @param {number} [timeout=10000] - The maximum time to wait in milliseconds.
   * @returns {Promise<object>} The nexacro form component for the search area.
   * @throws {Error} If the form is not ready within the timeout period.
   */
  async function waitForFullForm(timeout = 10000) {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      try {
        const app = window.nexacro.getApplication();
        const form =
          app?.mainframe?.HFrameSet00?.VFrameSet00?.FrameSet?.STMB011_M0?.form;
        const search = form?.div_workForm?.form?.div_search?.form;
        // Check if the date component and its 'set_value' method are available
        if (search?.calFromDay && typeof search.calFromDay.set_value === "function") {
          return search;
        }
      } catch (e) {
        // Ignore errors while polling, as objects may not exist yet
      }
      await delay(300);
    }
    throw new Error("Timeout: Nexacro search form component (calFromDay) not ready.");
  }

  /**
   * Generates an array of date strings in YYYYMMDD format for the past n days.
   * @param {number} [n=7] - The number of past days to generate dates for.
   * @returns {string[]} An array of date strings.
   */
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
    return dates;
  }

  /**
   * Simulates a robust mouse click on an element.
   * Note: This may be used by other automation scripts.
   * @param {Element} el - The element to click.
   */
  function clickByElement(el) {
    const rect = el.getBoundingClientRect();
    const commonProps = {
      bubbles: true,
      cancelable: true,
      view: window,
      clientX: rect.left + rect.width / 2,
      clientY: rect.top + rect.height / 2
    };
    el.dispatchEvent(new MouseEvent("mousedown", commonProps));
    el.dispatchEvent(new MouseEvent("mouseup", commonProps));
    el.dispatchEvent(new MouseEvent("click", commonProps));
  }

  /**
   * Sets the date in the form, triggers a search, and waits for results.
   * This version is improved to use the nexacro component API directly for better reliability.
   * @param {string} dateStr - The date string in YYYYMMDD format.
   */
  async function inputDateAndSearch(dateStr) {
    try {
      // Ensure the main form is ready before proceeding
      const searchForm = await waitForFullForm();

      // Set the date value using the component's native 'set_value' method
      searchForm.calFromDay.set_value(dateStr);
      await delay(100); // A brief pause for the UI to update

      // Access the search button directly through the nexacro application object path
      const app = window.nexacro.getApplication();
      const mainForm = app.mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form;
      const searchBtn = mainForm.div_cmmbtn.form.F_10;

      if (!searchBtn || typeof searchBtn.click !== 'function') {
        throw new Error("Search button (F_10) component not found or is not clickable.");
      }
      
      // Trigger the search using the component's native 'click' method
      searchBtn.click();
      console.log(`조회 실행 - 날짜: ${dateStr}`);

      // Wait for the results grid to be populated to confirm the search is complete.
      // This is more reliable than a fixed delay.
      await waitForElement("div[id*='gdList.body'][id$='0_0:text']", 15000);

    } catch (err) {
      // Record and re-throw the error for the main function to handle
      const errorMessage = `❌ [${dateStr}] 처리 실패: ${err.message}`;
      window.automation.error = errorMessage;
      console.error(errorMessage, err);
      throw err;
    }
  }

  /**
   * Main automation function to collect data for the past 7 days.
   */
  async function collectPast7Days() {
    try {
      window.automation.error = null;
      const dates = getPastDates(7);
      console.log(`과거 7일 데이터 수집 시작: ${dates.join(', ')}`);

      for (const date of dates) {
        await inputDateAndSearch(date);
        
        // Check for and execute the next step in the automation chain
        if (typeof window.automation.autoClickAllMidCodesAndProducts === "function") {
          await window.automation.autoClickAllMidCodesAndProducts();
        } else {
          // This error will be caught by the outer catch block
          throw new Error("통합 수집 함수(autoClickAllMidCodesAndProducts)가 정의되지 않았습니다.");
        }
        await delay(1000); // Wait a second between processing each day
      }
      console.log("✅ 과거 7일치 수집 완료");
    } catch (err) {
      // Log the final error that stopped the process
      console.error("⛔ collectPast7Days 실패:", err.message);
    }
  }

  // Expose the main function to be called from the browser console or another script
  window.automation.collectPast7Days = collectPast7Days;
  console.log("`window.automation.collectPast7Days()`를 호출하여 수집을 시작하세요.");
})();