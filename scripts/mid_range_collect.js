(() => {
  const start = window.__MID_RANGE_START__ || null;
  const end = window.__MID_RANGE_END__ || null;
  if (typeof window.collectMidProducts === 'function') {
    window.collectMidProducts(start, end);
  } else {
    console.warn('collectMidProducts 함수가 정의되어 있지 않습니다. auto_collect_mid_products.js를 먼저 실행하세요.');
  }
})();
