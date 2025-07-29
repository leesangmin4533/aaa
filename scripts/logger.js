(() => {
  function initLogger() {
    window.automationHelpers = window.automationHelpers || {};
    if (typeof window.automationHelpers.hookConsole === 'function') {
      window.automationHelpers.hookConsole(window.automation || {});
    }
  }

  window.automationHelpers = window.automationHelpers || {};
  window.automationHelpers.initLogger = initLogger;
})();
