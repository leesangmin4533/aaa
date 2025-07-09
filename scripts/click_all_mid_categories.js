(() => {
  const cells = [...document.querySelectorAll("div[id*='gdList.body'][id$='_0:text']")];
  cells.forEach(cell => {
    const target = document.getElementById(cell.id.replace(':text', ''));
    if (target) {
      const rect = target.getBoundingClientRect();
      ['mousedown','mouseup','click'].forEach(type => {
        target.dispatchEvent(new MouseEvent(type, {
          bubbles: true,
          cancelable: true,
          view: window,
          clientX: rect.left + rect.width / 2,
          clientY: rect.top + rect.height / 2
        }));
      });
    }
  });
})();
