(() => {
  function initLogger() {
    window.automation = window.automation || {};
    Object.assign(window.automation, {
      logs: [],
      errors: [],
      error: null,
      parsedData: null,
      isCollecting: false,
    });
    window.__midCategoryLogs__ = window.__midCategoryLogs__ || [];

    const origConsoleLog = console.log;
    console.log = function (...args) {
      window.automation.logs.push(
        args.map(a => (typeof a === 'object' ? JSON.stringify(a, null, 2) : String(a))).join(' ')
      );
      return origConsoleLog.apply(console, args);
    };

    const origConsoleError = console.error;
    console.error = function (...args) {
      const msg = '[ERROR] ' + args.map(a => (a instanceof Error ? a.message : typeof a === 'object' ? JSON.stringify(a, null, 2) : String(a))).join(' ');
      window.automation.logs.push(msg);
      window.automation.errors.push(msg);
      return origConsoleError.apply(console, args);
    };
  }

  window.automationHelpers = window.automationHelpers || {};
  window.automationHelpers.initLogger = initLogger;
})();
