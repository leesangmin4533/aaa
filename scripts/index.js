// Logger setup
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
    throw new Error('mainForm이 15초 내 생성되지 않았습니다.');
  };

  async function getNestedNexacroComponent(pathComponents, initialScope, timeout = 30000) {
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

  Object.assign(window.automationHelpers, {
    delay,
    getNexacroApp,
    getMainForm,
    getNexacroComponent,
    waitForTransaction,
    selectMiddleCodeRow,
    ensureMainFormLoaded,
    getNestedNexacroComponent,
  });
})();

// Dataset utils
(() => {
  function parseDetailDataset(dsDetail, midCode, midName) {
    const products = [];
    if (!dsDetail) return products;
    for (let i = 0; i < dsDetail.getRowCount(); i++) {
      products.push({
        midCode,
        midName,
        productCode: dsDetail.getColumn(i, 'ITEM_CD'),
        productName: dsDetail.getColumn(i, 'ITEM_NM'),
        sales: parseInt(dsDetail.getColumn(i, 'SALE_QTY') || 0, 10),
        order_cnt: parseInt(dsDetail.getColumn(i, 'ORD_QTY') || 0, 10),
        purchase: parseInt(dsDetail.getColumn(i, 'BUY_QTY') || 0, 10),
        disposal: parseInt(dsDetail.getColumn(i, 'DISUSE_QTY') || 0, 10),
        stock: parseInt(dsDetail.getColumn(i, 'STOCK_QTY') || 0, 10),
      });
    }
    return products;
  }
  function parseListDataset(dsList) {
    const mids = [];
    if (!dsList) return mids;
    for (let i = 0; i < dsList.getRowCount(); i++) {
      mids.push({
        code: dsList.getColumn(i, 'MID_CD'),
        name: dsList.getColumn(i, 'MID_NM'),
        expectedQuantity: parseInt(dsList.getColumn(i, 'SALE_QTY') || 0, 10),
        row: i,
      });
    }
    return mids;
  }
  Object.assign(window.automationHelpers, {
    parseDetailDataset,
    parseListDataset,
  });
})();

// Automation core
(() => {
  const {
    delay,
    getMainForm,
    getNestedNexacroComponent,
    getNexacroComponent,
    selectMiddleCodeRow,
    ensureMainFormLoaded,
    parseDetailDataset,
    parseListDataset,
  } = window.automationHelpers;

  async function collectProducts(midCode, midName) {
    const dsDetail = getMainForm()?.div_workForm?.form?.dsDetail;
    return parseDetailDataset(dsDetail, midCode, midName);
  }
  async function getAllMidCodes() {
    const dsList = getMainForm()?.div_workForm?.form?.dsList;
    return parseListDataset(dsList);
  }
  async function runCollectionForDate(dateStr) {
    if (window.automation.isCollecting) return;
    window.automation.isCollecting = true;
    window.automation.error = null;
    window.automation.parsedData = null;
    try {
      await ensureMainFormLoaded();
      const mainForm = getMainForm();
      const calFromDay = await getNestedNexacroComponent(['div_workForm','form','div2','form','div_search','form','calFromDay'], mainForm, 30000);
      const searchBtn = await getNexacroComponent('F_10', mainForm.div_cmmbtn.form, 30000);
      const dateInput = calFromDay.calendaredit;
      dateInput.set_value('');
      await delay(500);
      dateInput.set_value(dateStr);
      searchBtn.click();
      await new Promise((resolve,reject)=>{
        const iv=setInterval(()=>{
          const c=document.querySelector("div[id*='gdList.body'][id*='cell_0_0:text']");
          if(c&&c.innerText.trim()){clearInterval(iv);resolve();}
        },500);setTimeout(()=>{clearInterval(iv);reject(new Error('mid list timeout'));},120000);
      });
      await delay(700);
      const mids = await getAllMidCodes();
      const map=new Map();
      for(const mid of mids){
        selectMiddleCodeRow(mid.row);
        await new Promise((resolve,reject)=>{
          const iv=setInterval(()=>{
            const c=document.querySelector("div[id*='gdDetail.body'][id*='cell_0_0:text']");
            if(c&&c.innerText.trim()){clearInterval(iv);resolve();}
          },500);setTimeout(()=>{clearInterval(iv);reject(new Error('detail timeout'));},120000);
        });
        await delay(700);
        const products=await collectProducts(mid.code,mid.name);
        products.forEach(p=>{
          const key=`${p.midCode}_${p.productCode}`;
          if(map.has(key)){
            const ex=map.get(key);
            ex.sales+=p.sales;ex.order_cnt+=p.order_cnt;ex.purchase+=p.purchase;ex.disposal+=p.disposal;ex.stock+=p.stock;
          }else{map.set(key,p);}
        });
      }
      window.automation.parsedData=Array.from(map.values());
      window.automation.midCodesSnapshot=mids;
    }catch(e){
      console.error('데이터 수집 오류:',e.message);
      window.automation.error=e.message;
    }finally{
      window.automation.isCollecting=false;
    }
  }

  async function verifyMidSaleQty(midInfo){
    if(!window.automation.parsedData) return false;
    const products=window.automation.parsedData.filter(p=>p.midCode===midInfo.code);
    const actual=products.reduce((s,p)=>s+p.sales,0);
    return actual===midInfo.expectedQuantity;
  }
  async function runSaleQtyVerification(){
    const mids=window.automation.midCodesSnapshot||[];
    const failed=[];
    for(const m of mids){
      const ok=await verifyMidSaleQty(m);
      if(!ok) failed.push(m.code);
    }
    return {success:failed.length===0, failed_codes:failed};
  }
  Object.assign(window.automationHelpers,{runCollectionForDate,runSaleQtyVerification});
})();

(() => {
  window.automation = window.automation || {};
  window.automationHelpers.initLogger();
  window.automation.runCollectionForDate = window.automationHelpers.runCollectionForDate;
  window.automation.runSaleQtyVerification = window.automationHelpers.runSaleQtyVerification;
})();
