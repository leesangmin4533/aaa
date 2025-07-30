(() => {
  const delay = (ms) => new Promise(res => setTimeout(res, ms));

  function getNexacroApp() {
    const app = window.nexacro && typeof window.nexacro.getApplication === 'function' ? window.nexacro.getApplication() : null;
    if (app) {
      console.log("[getNexacroApp] Nexacro Application 객체를 찾았습니다.");
    } else {
      console.warn("[getNexacroApp] Nexacro Application 객체를 찾을 수 없습니다.");
    }
    return app;
  }

  function getMainForm() {
    const app = getNexacroApp();
    const mainForm = app?.mainframe?.HFrameSet00?.VFrameSet00?.FrameSet?.STMB011_M0?.form || null;
    if (mainForm) {
      console.log("[getMainForm] 메인 폼(STMB011_M0)을 찾았습니다.");
    } else {
      console.warn("[getMainForm] 메인 폼(STMB011_M0)을 찾을 수 없습니다. 경로 확인 필요.");
    }
    return mainForm;
  }

  async function getNexacroComponent(componentId, initialScope = null, timeout = 10000) {
    console.log(`[getNexacroComponent] 컴포넌트 대기 중: "${componentId}" (시간 초과: ${timeout}ms)`);
    const start = Date.now();
    let currentScope = initialScope;

    while (Date.now() - start < timeout) {
      if (!currentScope) {
        currentScope = getMainForm();
        if (!currentScope) {
          await delay(500);
          continue;
        }
      }

      if (currentScope && typeof currentScope.lookup === 'function') {
        const component = currentScope.lookup(componentId);
        if (component) {
          console.log(`[getNexacroComponent] 성공! 컴포넌트 찾음: "${componentId}"`);
          return component;
        }
      } else {
        console.warn(`[getNexacroComponent] 현재 스코프가 유효하지 않거나 lookup 함수가 없습니다. 컴포넌트: "${componentId}"`);
      }
      await delay(500);
    }
    console.error(`[getNexacroComponent] 시간 초과! 컴포넌트를 찾을 수 없습니다: "${componentId}"`);
    return null;
  }

  async function getNestedNexacroComponent(pathComponents, initialScope, timeout = 30000) {
    let currentScope = initialScope;
    for (let i = 0; i < pathComponents.length; i++) {
      const componentId = pathComponents[i];
      if (!currentScope) {
        throw new Error(`이전 스코프가 null입니다. 경로: ${pathComponents.slice(0, i).join('.')}`);
      }

      if (componentId === 'form') {
        currentScope = currentScope.form;
        if (!currentScope) {
          throw new Error(`'${pathComponents.slice(0, i).join('.')}' 내에 'form' 속성을 찾을 수 없습니다.`);
        }
        console.log(`[getNestedNexacroComponent] 속성 접근: ${pathComponents.slice(0, i + 1).join('.')}`);
      } else {
        currentScope = await getNexacroComponent(componentId, currentScope, timeout);
        if (!currentScope) {
          throw new Error(`'${pathComponents.slice(0, i).join('.')}' 내에 컴포넌트 '${componentId}'를 찾을 수 없습니다.`);
        }
      }
    }
    return currentScope;
  }

  function waitForTransaction(svcID, timeout = 15000) {
    console.log(`[waitForTransaction] 서비스 ID 대기 중: '${svcID}' (시간 초과: ${timeout}ms)`);
    return new Promise((resolve, reject) => {
      const form = getMainForm();
      if (!form) {
        return reject(new Error("메인 폼을 찾을 수 없어 트랜잭션을 기다릴 수 없습니다."));
      }

      let originalCallback = form.fn_callback;
      let callbackRestored = false;

      const restoreCallback = () => {
        if (!callbackRestored) {
          form.fn_callback = originalCallback;
          callbackRestored = true;
        }
      };

      const timeoutId = setTimeout(() => {
        restoreCallback();
        console.error(`[waitForTransaction] 시간 초과! 서비스 ID '${svcID}'가 ${timeout}ms 후 타임아웃되었습니다.`);
        reject(new Error(`'${svcID}' 트랜잭션 대기 시간 초과 (${timeout}ms).`));
      }, timeout);

      form.fn_callback = function(serviceID, errorCode, errorMsg) {
        if (typeof originalCallback === 'function') {
          originalCallback.apply(this, arguments);
        }

        const baseServiceID = serviceID.split('|')[0];
        console.log(`[waitForTransaction] fn_callback 호출됨: 수신 서비스 ID='${serviceID}', 기본 ID='${baseServiceID}', 기대 ID='${svcID}'`);

        if (baseServiceID === svcID) {
          clearTimeout(timeoutId);
          if (errorCode >= 0) {
            console.log(`[waitForTransaction] '${svcID}' 트랜잭션 성공적으로 완료. Promise 해결.`);
            resolve();
          } else {
            console.error(`[waitForTransaction] '${svcID}' 트랜잭션 실패: ${errorMsg} (코드: ${errorCode})`);
            reject(new Error(`'${svcID}' 트랜잭션 실패: ${errorMsg}`));
          }
          restoreCallback();
        } else {
          console.log(`[waitForTransaction] 다른 트랜잭션 완료: 수신 서비스 ID='${serviceID}'. 여전히 '${svcID}' 대기 중.`);
        }
      };
    });
  }

  function selectMiddleCodeRow(rowIndex) {
    const f = getMainForm();
    const gList = f?.div_workForm?.form?.div2?.form?.gdList;
    if (!gList) throw new Error("gdList가 존재하지 않습니다.");

    gList.selectRow(rowIndex);
    const evt = new nexacro.GridClickEventInfo(gList, "oncellclick", false, false, false, false, 0, 0, rowIndex, rowIndex);
    gList.oncellclick._fireEvent(gList, evt);
  }

  const ensureMainFormLoaded = async () => {
    for (let i = 0; i < 50; i++) {
      const form = getMainForm();
      if (form) return true;
    await delay(500);
    }
    throw new Error("mainForm이 15초 내 생성되지 않았습니다.");
  };

  // window.automation 객체에 헬퍼 함수들 노출
  Object.assign(window.automation, {
    delay,
    getNexacroApp,
    getMainForm,
    getNexacroComponent,
    getNestedNexacroComponent,
    waitForTransaction,
    selectMiddleCodeRow,
    ensureMainFormLoaded,
  });
})();
