(() => {
  // 콘솔 로그를 후킹하여 window.automation.logs에 저장
  const origConsoleLog = console.log;
  console.log = function(...args) {
    window.automation.logs.push(args.map(arg => (typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg))).join(' '));
    return origConsoleLog.apply(console, args);
  };
  // 콘솔 에러를 후킹하여 window.automation.logs 및 window.automation.errors에 저장
  const origConsoleError = console.error;
  console.error = function(...args) {
    const errorMsg = "[ERROR] " + args.map(arg => {
      if (arg instanceof Error) {
        return arg.message; // Extract message from Error objects
      }
      return (typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg));
    }).join(' ');
    window.automation.logs.push(errorMsg);
    window.automation.errors.push(errorMsg);
    return origConsoleError.apply(console, args);
  };
})();