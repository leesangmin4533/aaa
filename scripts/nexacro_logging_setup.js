(() => {
  window.automationHelpers = window.automationHelpers || {};
  if (typeof window.automationHelpers.hookConsole === 'function') {
    window.automationHelpers.hookConsole(window.automation || {});
  }
})();
