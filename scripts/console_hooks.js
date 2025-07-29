(() => {
  function hookConsole(saveTarget = window.automation) {
    saveTarget.logs = saveTarget.logs || [];
    saveTarget.errors = saveTarget.errors || [];

    const origLog = console.log;
    console.log = (...args) => {
      const text = args
        .map(a => (typeof a === 'object' ? JSON.stringify(a, null, 2) : String(a)))
        .join(' ');
      saveTarget.logs.push(text);
      return origLog.apply(console, args);
    };

    const origErr = console.error;
    console.error = (...args) => {
      const text = '[ERROR] ' +
        args
          .map(a =>
            a instanceof Error
              ? a.message
              : typeof a === 'object'
                ? JSON.stringify(a, null, 2)
                : String(a)
          )
          .join(' ');
      saveTarget.logs.push(text);
      saveTarget.errors.push(text);
      return origErr.apply(console, args);
    };
  }

  window.automationHelpers = window.automationHelpers || {};
  window.automationHelpers.hookConsole = hookConsole;
})();
