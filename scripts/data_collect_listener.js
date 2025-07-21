(() => {
  // 1. Setup and Utilities
  window.automation = window.automation || {};
  window.automation.liveData = window.automation.liveData || [];
  const seen = new Set(window.automation.liveData);

  let currentMidCode = '';
  let currentMidName = '';
  let observer = null; // Observer 인스턴스를 저장할 변수

  // 특정 요소가 DOM에 나타날 때까지 기다리는 유틸리티 함수
  function waitForElement(selector, timeout = 15000) {
    return new Promise((resolve, reject) => {
      const interval = setInterval(() => {
        const el = document.querySelector(selector);
        if (el && el.offsetParent !== null) {
          clearInterval(interval);
          resolve(el);
        }
      }, 300);
      setTimeout(() => {
        clearInterval(interval);
        reject(new Error(`Timeout waiting for element: ${selector}`));
      }, timeout);
    });
  }

  // 함수 호출을 지연시키는 디바운스 유틸리티
  function debounce(func, delay) {
    let timeout;
    return function(...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), delay);
    };
  }

  // 2. Core Data Collection Logic (기존과 거의 동일)
  function getText(row, col) {
    const el = document.querySelector(
      `div[id*='gdDetail.body'][id*='cell_${row}_${col}'][id$=':text']`
    );
    return el?.innerText?.trim() || '';
  }

  function collectLines() {
    const rows = [
      ...document.querySelectorAll(
        "div[id*='gdDetail.body'][id*='cell_'][id$='_0:text']"
      )
    ];
    const lines = [];
    for (const el of rows) {
      const row = el.id.match(/cell_(\d+)_0:text/)?.[1];
      if (!row) continue;
      const line = [
        currentMidCode || '0',
        currentMidName || '',
        getText(row, 0) || '0',
        getText(row, 1) || '0',
        getText(row, 2) || '0',
        getText(row, 3) || '0',
        getText(row, 4) || '0',
        getText(row, 5) || '0',
        getText(row, 6) || '0'
      ].join('\t');
      if (!seen.has(line)) {
        seen.add(line);
        lines.push(line);
      }
    }
    if (lines.length) {
      window.automation.liveData.push(...lines);
      if (window.automation.logs) {
        window.automation.logs.push(`📥 [Observer] added ${lines.length} lines`);
      }
    }
  }

  // 3. MutationObserver 설정
  const debouncedCollectLines = debounce(collectLines, 300); // 300ms 디바운스 적용

  function setupObserver(targetNode) {
    if (observer) {
      observer.disconnect(); // 이전 Observer 연결 해제
    }

    const config = { childList: true, subtree: true };
    const callback = function(mutationsList, obs) {
      // DOM 변경이 감지되면 디바운스된 수집 함수 호출
      debouncedCollectLines();
    };

    observer = new MutationObserver(callback);
    observer.observe(targetNode, config);
  }

  // 4. `mid-clicked` 이벤트를 사용하여 Observer 생명주기 관리
  document.addEventListener('mid-clicked', async (event) => {
    currentMidCode = event.detail?.code || '';
    currentMidName = event.detail?.midName || '';

    try {
      // 새로운 상품 그리드 body가 나타날 때까지 대기
      const gridBody = await waitForElement("div[id*='gdDetail.body']");
      
      // 새로운 그리드에 Observer 설정
      setupObserver(gridBody);
      
      // Observer가 첫 변경을 놓칠 수 있으므로, 초기 데이터 수집을 한 번 실행
      setTimeout(collectLines, 200);

    } catch (error) {
      console.error('Failed to set up MutationObserver:', error);
    }
  });

})();