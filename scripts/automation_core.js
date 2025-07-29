(() => {
  const {
    delay,
    getMainForm,
    getNestedNexacroComponent,
    getNexacroComponent,
    selectMiddleCodeRow,
    ensureMainFormLoaded,
  } = window.automationHelpers;
  const { parseDetailDataset, parseListDataset } = window.automationHelpers;

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

      const calFromDay = await getNestedNexacroComponent(
        ['div_workForm', 'form', 'div2', 'form', 'div_search', 'form', 'calFromDay'],
        mainForm,
        30000,
      );
      const searchBtn = await getNexacroComponent('F_10', mainForm.div_cmmbtn.form, 30000);
      const dateInput = calFromDay.calendaredit;
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
      } catch (e) {
        console.error('strYmd proxy failed:', e.message);
      }

      const btn = [...document.querySelectorAll('div')]
        .find(el => el.innerText?.trim() === '조 회' && el.offsetParent !== null);
      if (btn) {
        const rect = btn.getBoundingClientRect();
        ['mousedown', 'mouseup', 'click'].forEach(evt =>
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

      await new Promise((resolve, reject) => {
        const iv = setInterval(() => {
          const cell = document.querySelector("div[id*='gdList.body'][id*='cell_0_0:text']");
          if (cell && cell.innerText.trim()) {
            clearInterval(iv);
            resolve();
          }
        }, 500);
        setTimeout(() => { clearInterval(iv); reject(new Error('mid list timeout')); }, 120000);
      });
      await delay(700);

      const mids = await getAllMidCodes();
      const allProductsMap = new Map();

      for (const mid of mids) {
        selectMiddleCodeRow(mid.row);
        await new Promise((resolve, reject) => {
          const iv = setInterval(() => {
            const cell = document.querySelector("div[id*='gdDetail.body'][id*='cell_0_0:text']");
            if (cell && cell.innerText.trim()) {
              clearInterval(iv);
              resolve();
            }
          }, 500);
          setTimeout(() => { clearInterval(iv); reject(new Error('detail timeout')); }, 120000);
        });
        await delay(700);

        const products = await collectProducts(mid.code, mid.name);
        products.forEach(p => {
          const key = `${p.midCode}_${p.productCode}`;
          if (allProductsMap.has(key)) {
            const ex = allProductsMap.get(key);
            ex.sales += p.sales;
            ex.order_cnt += p.order_cnt;
            ex.purchase += p.purchase;
            ex.disposal += p.disposal;
            ex.stock += p.stock;
          } else {
            allProductsMap.set(key, p);
          }
        });
      }

      window.automation.parsedData = Array.from(allProductsMap.values());
      window.automation.midCodesSnapshot = mids;
    } catch (e) {
      console.error('데이터 수집 오류:', e.message);
      window.automation.error = e.message;
    } finally {
      window.automation.isCollecting = false;
    }
  }

  async function verifyMidSaleQty(midInfo) {
    if (!window.automation.parsedData) return false;
    const products = window.automation.parsedData.filter(p => p.midCode === midInfo.code);
    const actual = products.reduce((sum, p) => sum + p.sales, 0);
    return actual === midInfo.expectedQuantity;
  }

  async function runSaleQtyVerification() {
    const mids = window.automation.midCodesSnapshot || [];
    const failed = [];
    for (const m of mids) {
      const ok = await verifyMidSaleQty(m);
      if (!ok) failed.push(m.code);
    }
    return { success: failed.length === 0, failed_codes: failed };
  }

  window.automationHelpers = window.automationHelpers || {};
  Object.assign(window.automationHelpers, {
    runCollectionForDate,
    runSaleQtyVerification,
  });
})();
