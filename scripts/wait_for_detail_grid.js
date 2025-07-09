(() => {
  const start = Date.now();
  function poll() {
    const exists = document.querySelector("div[id*='gdDetail.body'][id*='cell_0_0'][id$=':text']");
    if (exists) {
      window.__gridReady = true;
    } else if (Date.now() - start < 5000) {
      setTimeout(poll, 200);
    } else {
      window.__gridReady = false;
    }
  }
  poll();
})();
