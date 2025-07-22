(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  if (!window.automation) window.automation = {};
  window.automation.error = null;
  window.automation.logs = [];
  window.automation.errors = [];

  const origConsoleLog = console.log;
  console.log = function (...args) {
    window.automation.logs.push(args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg))).join(' '));
    return origConsoleLog.apply(console, args);
  };

  const origConsoleError = console.error;
  console.error = function (...args) {
    window.automation.logs.push("[ERROR] " + args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg))).join(' '));
    window.automation.errors.push("[ERROR] " + args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg))).join(' '));
    return origConsoleError.apply(console, args);
  };

  const log = (...args) => {
    const message = args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg))).join(' ');
    console.log(message);
    return message;
  };

  const errorLog = (...args) => {
    const message = "[오류] " + args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg))).join(' ');
    console.error(message);
    return message;
  };

  async function waitForSelector(selector, timeout = 120000) {
    log(`[waitForSelector] 대기중: "${selector}" (시간 초과: ${timeout}ms)`);
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const el = document.querySelector(selector);
      if (el && el.offsetParent !== null) {
        log(`[waitForSelector] 성공: "${selector}" 발견`);
        return el;
      }
      await delay(300);
    }
    errorLog(`시간 초과: "${selector}"를 찾을 수 없습니다.`);
    throw new Error(`시간 초과: "${selector}"를 찾을 수 없습니다.`);
  }

  async function waitForFullForm(timeout = 120000) {
    log(`[waitForFullForm] 폼 준비 대기... (시간 초과: ${timeout}ms)`);
    const start = Date.now();
    while (Date.now() - start < timeout) {
      try {
        const app = window.nexacro.getApplication();
        const form = app?.mainframe?.HFrameSet00?.VFrameSet00?.FrameSet?.STMB011_M0?.form;
        const search = form?.div_workForm?.form?.div2?.form?.div_search?.form;
        if (search?.calFromDay && typeof search.calFromDay.set_value === "function") {
          log('[waitForFullForm] 폼 준비 완료');
          return search;
        }
      } catch (e) {
        // Ignore errors during polling
      }
      await delay(300);
    }
    errorLog('폼이 준비되지 않았습니다.');
    throw new Error('폼이 준비되지 않았습니다.');
  }

  async function inputDateAndSearch(dateStr) {
    log(`[inputDateAndSearch] 날짜 처리 시작: ${dateStr}`);
    try {
      const searchForm = await waitForFullForm();

      log(`[inputDateAndSearch] 날짜 값 설정 시도: ${dateStr}`);
      searchForm.calFromDay.set_value(dateStr);
      await delay(100);
      log(`[inputDateAndSearch] 날짜 입력 완료: ${searchForm.calFromDay.value}`);

      const app = window.nexacro.getApplication();
      const mainForm = app.mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form;
      const searchBtn = mainForm.div_cmmbtn.form.F_10;

      if (!searchBtn || typeof searchBtn.click !== 'function') {
        errorLog('검색 버튼을 찾거나 클릭할 수 없습니다.');
        throw new Error('검색 버튼을 찾거나 클릭할 수 없습니다.');
      }
      
      log('[inputDateAndSearch] 검색 버튼 클릭');
      searchBtn.click();

      await waitForSelector("div[id*='gdList.body'][id$='0_0:text']", 15000);
      log(`[inputDateAndSearch] 결과 로드 완료: ${dateStr}`);

    } catch (err) {
      const errorMessage = `${dateStr} 검색 실패: ${err.message}`;
      window.automation.error = errorMessage;
      errorLog(errorMessage);
      throw err;
    }
  }

  // New function to collect data for a single date
  async function collectSingleDayData(dateStr) {
    log(`[collectSingleDayData] 시작: ${dateStr}`);
    try {
      window.automation.error = null; // Reset error for this run
      window.automation.parsedData = null; // Reset parsedData for this run

      log(`[collectSingleDayData] inputDateAndSearch 호출: ${dateStr}`);
      await inputDateAndSearch(dateStr);
      log(`[collectSingleDayData] inputDateAndSearch 완료: ${dateStr}`);
      
      log(`[collectSingleDayData] ${dateStr} 처리 완료, 상품 수집 시작`);
      if (typeof window.automation.autoClickAllMidCodesAndProducts === "function") {
        log("[collectSingleDayData] autoClickAllMidCodesAndProducts 실행");
        await window.automation.autoClickAllMidCodesAndProducts();
        log("[collectSingleDayData] autoClickAllMidCodesAndProducts 완료");
        
        if (window.automation.parsedData) {
          log(`[collectSingleDayData] 데이터 수집 성공: ${dateStr}, 길이: ${window.automation.parsedData.length}`);
          return { success: true, data: window.automation.parsedData };
        } else {
          const msg = `데이터가 없습니다: ${dateStr}`;
          log(`[collectSingleDayData] ${msg}`);
          return { success: true, data: [], message: msg }; // Return success with empty data if no data
        }
      } else {
        const msg = "autoClickAllMidCodesAndProducts 함수가 정의되지 않았습니다.";
        errorLog(`[collectSingleDayData] ${msg}`);
        window.automation.error = msg;
        return { success: false, message: msg };
      }
    } catch (err) {
      const errorMessage = `${dateStr} 처리 실패: ${err.message}`;
      window.automation.error = errorMessage;
      errorLog(errorMessage);
      return { success: false, message: errorMessage };
    }
  }

  // Expose the new function
  window.automation.collectSingleDayData = collectSingleDayData;
  log('스크립트가 로드되었습니다. 사용 방법: window.automation.collectSingleDayData(dateStr)');

})();
