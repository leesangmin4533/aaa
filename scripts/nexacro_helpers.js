// Logger setup
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

// Nexacro helpers
(() => {
  const delay = ms => new Promise(res => setTimeout(res, ms));

  function getNexacroApp() {
    const app = window.nexacro && typeof window.nexacro.getApplication === 'function'
      ? window.nexacro.getApplication()
      : null;
    return app;
  }

  function getMainForm() {
    const app = getNexacroApp();
    return app?.mainframe?.HFrameSet00?.VFrameSet00?.FrameSet?.STMB011_M0?.form || null;
  }

  async function getNexacroComponent(componentId, initialScope = null, timeout = 10000) {
    const start = Date.now();
    let scope = initialScope;
    while (Date.now() - start < timeout) {
      if (!scope) {
        scope = getMainForm();
        if (!scope) {
          await delay(500);
          continue;
        }
      }
      if (scope.lookup) {
        const c = scope.lookup(componentId);
        if (c) return c;
      }
      await delay(500);
    }
    return null;
  }

  function waitForTransaction(svcID, timeout = 15000) {
    return new Promise((resolve, reject) => {
      const form = getMainForm();
      if (!form) return reject(new Error('main form not found'));
      let original = form.fn_callback;
      let restored = false;
      const restore = () => {
        if (!restored) {
          form.fn_callback = original;
          restored = true;
        }
      };
      const tid = setTimeout(() => {
        restore();
        reject(new Error(`${svcID} timeout`));
      }, timeout);
      form.fn_callback = function(serviceID, errorCode, errorMsg) {
        if (typeof original === 'function') original.apply(this, arguments);
        if (serviceID.split('|')[0] === svcID) {
          clearTimeout(tid);
          restore();
          if (errorCode >= 0) resolve();
          else reject(new Error(errorMsg));
        }
      };
    });
  }

  function selectMiddleCodeRow(rowIndex) {
    const f = getMainForm();
    const g = f?.div_workForm?.form?.div2?.form?.gdList;
    if (!g) throw new Error('gdList not found');
    g.selectRow(rowIndex);
    const evt = new nexacro.GridClickEventInfo(g, 'oncellclick', false, false, false, false, 0, 0, rowIndex, rowIndex);
    g.oncellclick._fireEvent(g, evt);
  }

  const ensureMainFormLoaded = async () => {
    for (let i = 0; i < 50; i++) {
      if (getMainForm()) return true;
      await delay(500);
    }
    throw new Error('mainForm이 30초 내 생성되지 않았습니다.');
  };

  async function getNestedNexacroComponent(pathComponents, initialScope = null, timeout = 30000) {
    let scope = initialScope;
    for (let i = 0; i < pathComponents.length; i++) {
      const id = pathComponents[i];
      if (!scope) throw new Error(`scope null at ${pathComponents.slice(0, i).join('.')}`);
      if (scope[id]) {
        scope = scope[id];
      } else if (id === 'form') {
        scope = scope.form;
        if (!scope) throw new Error('form not found');
      } else {
        scope = await getNexacroComponent(id, scope, timeout);
        if (!scope) throw new Error(`${id} not found`);
      }
    }
    return scope;
  }

  async function clickElementById(id) {
    const el = document.getElementById(id);
    if (!el || el.offsetParent === null) {
      console.warn(`⛔ 클릭 실패: ID ${id} 요소를 찾을 수 없거나 화면에 표시되지 않습니다.`);
      return false;
    }
    try {
      const rect = el.getBoundingClientRect();
      ["mousedown", "mouseup", "click"].forEach(type =>
        el.dispatchEvent(new MouseEvent(type, {
          bubbles: true,
          cancelable: true,
          view: window,
          clientX: rect.left + rect.width / 2,
          clientY: rect.top + rect.height / 2
        }))
      );
      console.log(`✅ 클릭 성공: ID ${id}`);
      return true;
    } catch (e) {
      console.error(`클릭 이벤트 발생 중 오류: ${e}`);
      return false;
    }
  }

  Object.assign(window.automationHelpers, {
    delay,
    getNexacroApp,
    getMainForm,
    getNexacroComponent,
    waitForTransaction,
    selectMiddleCodeRow,
    ensureMainFormLoaded,
    getNestedNexacroComponent,
    clickElementById,
  });
})();