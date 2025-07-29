// Logger는 nexacro_helpers.js에서 정의됩니다.

// Automation core
(() => {
  const {
    delay,
    getMainForm,
    getNestedNexacroComponent,
    getNexacroComponent,
    selectMiddleCodeRow,
    ensureMainFormLoaded,
    collectProductsFromDataset,
    getAllMidCodesFromDataset,
    clickElementById,
  } = window.automationHelpers;

  async function collectProducts(midCode, midName) {
    return collectProductsFromDataset(midCode, midName);
  }
  async function getAllMidCodes() {
    return getAllMidCodesFromDataset();
  }
  async function runCollectionForDate(dateStr) {
    window.automation.logs.push(`[runCollectionForDate] Starting for date: ${dateStr}`);
    if (window.automation.isCollecting) {
      window.automation.logs.push("[runCollectionForDate] Already collecting, returning.");
      return;
    }
    window.automation.isCollecting = true;
    window.automation.error = null;
    window.automation.parsedData = null;
    try {
      window.automation.logs.push("[runCollectionForDate] Ensuring main form loaded...");
      await ensureMainFormLoaded();
      window.automation.logs.push("[runCollectionForDate] Main form loaded. Getting components...");
      const mainForm = getMainForm();
      const calFromDay = await getNestedNexacroComponent(['div_workForm','form','div2','form','div_search','form','calFromDay'], mainForm, 30000);
      const searchBtn = await getNexacroComponent('F_10', mainForm.div_cmmbtn.form, 30000);
      window.automation.logs.push("[runCollectionForDate] Components obtained. Setting date...");
      const dateInput = calFromDay.calendaredit;
      await clickElementById("mainframe.HFrameSet00.VFrameSet00.FrameSet.STMB011_M0.form.div_workForm.form.div2.form.div_search.form.calFromDay.calendaredit:input");
      dateInput.set_value('');
      await delay(500);
      dateInput.set_value(dateStr);

      const hyphenDate = dateStr.includes('-') ? dateStr
                          : dateStr.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3');
      try {
        Object.defineProperty(mainForm, 'strYmd', {
          configurable: true,
          get: () => hyphenDate,
          set: () => {}
        });
      } catch(e){
        window.automation.logs.push('[ERROR] strYmd proxy failed: '+e.message);
      }

      window.automation.logs.push(`[runCollectionForDate] Date set to ${dateStr}. Clicking search button...`);

      const btn = [...document.querySelectorAll('div')]
        .find(el => el.innerText?.trim() === '조 회' && el.offsetParent !== null);
      if (btn) {
        const rect = btn.getBoundingClientRect();
        ['mousedown','mouseup','click'].forEach(evt =>
          btn.dispatchEvent(new MouseEvent(evt, {
            bubbles: true,
            cancelable: true,
            view: window,
            clientX: rect.left + rect.width / 2,
            clientY: rect.top + rect.height / 2
          }))
        );
      } else {
        searchBtn.click();
      }
      window.automation.logs.push("[runCollectionForDate] Waiting for mid list to load...");
      await new Promise((resolve,reject)=>{
        const iv=setInterval(()=>{
          const c=document.querySelector("div[id*='gdList.body'][id*='cell_0_0:text']");
          if(c&&c.innerText.trim()){clearInterval(iv);resolve();}
        },500);setTimeout(()=>{clearInterval(iv);reject(new Error('mid list timeout'));},120000);
      });
      window.automation.logs.push("[runCollectionForDate] Mid list loaded. Delaying...");
      await delay(700);
      window.automation.logs.push("[runCollectionForDate] Getting all mid codes...");
      const mids = await getAllMidCodes();
      const map=new Map();
      window.automation.logs.push(`[runCollectionForDate] Found ${mids.length} mid codes. Starting iteration...`);
      for(const mid of mids){
        window.automation.logs.push(`[runCollectionForDate] Selecting mid code row: ${mid.row} (${mid.code})`);
        selectMiddleCodeRow(mid.row);
        window.automation.logs.push("[runCollectionForDate] Waiting for detail data to load...");
        await new Promise((resolve,reject)=>{
          const iv=setInterval(()=>{
            const c=document.querySelector("div[id*='gdDetail.body'][id*='cell_0_0:text']");
            if(c&&c.innerText.trim()){clearInterval(iv);resolve();}
          },500);setTimeout(()=>{clearInterval(iv);reject(new Error('detail timeout'));},120000);
        });
        window.automation.logs.push("[runCollectionForDate] Detail data loaded. Delaying...");
        await delay(700);
        window.automation.logs.push("[runCollectionForDate] Collecting products...");
        const products=await collectProducts(mid.code,mid.name);
        products.forEach(p=>{
          const key=`${p.midCode}_${p.productCode}`;
          if(map.has(key)){
            const ex=map.get(key);
            ex.sales+=p.sales;ex.order_cnt+=p.order_cnt;ex.purchase+=p.purchase;ex.disposal+=p.disposal;ex.stock+=p.stock;
          }else{map.set(key,p);}
        });
        window.automation.logs.push(`[runCollectionForDate] Collected ${products.length} products for mid code ${mid.code}. Map size: ${map.size}`);
      }
      window.automation.parsedData=Array.from(map.values());
      window.automation.midCodesSnapshot=mids;
      window.automation.logs.push("[runCollectionForDate] Collection finished successfully.");
    }catch(e){
      window.automation.logs.push(`[ERROR] 데이터 수집 오류: ${e.message}`);
      window.automation.error=e.message;
      window.automation.logs.push("[runCollectionForDate] Collection failed.");
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
