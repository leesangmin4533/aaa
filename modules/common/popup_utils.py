"""Utilities for closing pop-up windows during automation."""


POPUP_CLOSE_SCRIPT = """
return (function () {
  let closed = 0;
  let closedIds = new Set();

  const allCloseCandidates = [];

  // \ub9d0\uae30\uc801 \uad6c\uc870 A
  const popupAList = Array.from(document.querySelectorAll('[id*="STCM230_P1"]'));
  popupAList.forEach(popup => {
    const closeBtn = popup.querySelector('[id$="btnClose"]');
    if (closeBtn) {
      allCloseCandidates.push(closeBtn);
    }
  });

  // \uc77c\ubc18 \uad6c\uc870 B
  const popupBList = Array.from(document.querySelectorAll('div')).filter(div => {
    const style = window.getComputedStyle(div);
    const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    const isCentered = style.position === 'fixed' || style.position === 'absolute';
    const isLarge = div.offsetWidth > 300 && div.offsetHeight > 200;
    return isVisible && isCentered && isLarge;
  });

  popupBList.forEach(div => {
    const buttons = div.querySelectorAll('button, a, div');
    buttons.forEach(btn => {
      const txt = btn.innerText?.trim();
      const isClickable =
        btn.onclick ||
        btn.getAttribute('role') === 'button' ||
        /btn|nexabutton/.test(btn.className);

      const btnId = btn.id || btn.getAttribute('name') || btn.outerHTML.slice(0, 60);
      if (
        isClickable &&
        /(\ub2eb\uae30|\ud655\uc778|\ub2e4\uc2dc \ubcf4\uc9c0 \uc54a\uae30)/.test(txt) &&
        !closedIds.has(btnId)
      ) {
        allCloseCandidates.push(btn);
        closedIds.add(btnId);
      }
    });
  });

  const results = [];

  allCloseCandidates.forEach(btn => {
    try {
      btn.click();
      closed++;
      results.push(`${btn.innerText} / ${btn.id || '[no-id]'}`);
    } catch (e) {
      results.push(`[\uc2e4\ud328] ${btn.innerText} / ${btn.id || '[no-id]'}`);
    }
  });

  return { count: closed, targets: results };
})();
"""


def close_popups(driver):
    """Execute JavaScript in ``driver`` to close known pop-ups and log results."""

    result = driver.execute_script(POPUP_CLOSE_SCRIPT)
    print("닫기 시도 대상:", result)
    return result.get("count", 0)
