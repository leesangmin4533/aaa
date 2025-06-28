"""Utilities for closing pop-up windows during automation."""


POPUP_CLOSE_SCRIPT = """
return (function () {
  let closed = 0;
  const clickedKeys = new Set();
  const closedIds = [];

  const allCloseCandidates = [];

  // === 1. \ube14\ub7ec \uac78\ub9b0 \uc694\uc18c \uc6b0\uc120 \ud0d0\uc9c0
  const blurredDivs = Array.from(document.querySelectorAll('div')).filter(div => {
    const style = window.getComputedStyle(div);
    return style.filter.includes('blur') || style.backdropFilter.includes('blur');
  });

  blurredDivs.forEach(div => {
    const buttons = div.querySelectorAll('button, a, div');
    buttons.forEach(btn => {
      const txt = btn.innerText?.trim();
      const isClickable =
        btn.onclick ||
        btn.getAttribute('role') === 'button' ||
        /btn|nexabutton/.test(btn.className);
      const key = btn.id || btn.outerHTML.slice(0, 100);
      if (
        isClickable &&
        /(\ub2eb\uae30|\ud655\uc778|\ub2e4\uc2dc \ubcf4\uc9c0 \uc54a\uae30)/.test(txt) &&
        !clickedKeys.has(key)
      ) {
        allCloseCandidates.push(btn);
        clickedKeys.add(key);
      }
    });
  });

  // === 2. \uba85\uc2dc\uc801 \uad6c\uc870 STCM230_P1
  const popupAList = Array.from(document.querySelectorAll('[id*="STCM230_P1"]'));
  popupAList.forEach(popup => {
    const closeBtn = popup.querySelector('[id$="btnClose"]');
    if (closeBtn) {
      const key = closeBtn.id || closeBtn.outerHTML.slice(0, 100);
      if (!clickedKeys.has(key)) {
        allCloseCandidates.push(closeBtn);
        clickedKeys.add(key);
      }
    }
  });

  // === 3. \uc77c\ubc18 \ud328\ud134 \uad6c\uc870
  const popupBList = Array.from(document.querySelectorAll('div')).filter(div => {
    const style = window.getComputedStyle(div);
    return (
      style.display !== 'none' &&
      style.visibility !== 'hidden' &&
      style.opacity !== '0' &&
      (style.position === 'fixed' || style.position === 'absolute') &&
      div.offsetWidth > 300 &&
      div.offsetHeight > 200
    );
  });

  popupBList.forEach(div => {
    const buttons = div.querySelectorAll('button, a, div');
    buttons.forEach(btn => {
      const txt = btn.innerText?.trim();
      const isClickable =
        btn.onclick ||
        btn.getAttribute('role') === 'button' ||
        /btn|nexabutton/.test(btn.className);
      const key = btn.id || btn.outerHTML.slice(0, 100);
      if (
        isClickable &&
        /(\ub2eb\uae30|\ud655\uc778|\ub2e4\uc2dc \ubcf4\uc9c0 \uc54a\uae30)/.test(txt) &&
        !clickedKeys.has(key)
      ) {
        allCloseCandidates.push(btn);
        clickedKeys.add(key);
      }
    });
  });

  // === \ud074\ub9ad \uc2e4\ud589
  allCloseCandidates.forEach(btn => {
    try {
      btn.click();
      closed++;
      closedIds.push(`${btn.innerText || '[no-text]'} / ${btn.id || '[no-id]'}`);
    } catch (e) {
      closedIds.push(`[\uc2e4\ud328] ${btn.innerText || '[no-text]'} / ${btn.id || '[no-id]'}`);
    }
  });

  return { count: closed, targets: closedIds };
})();
"""


def close_popups(driver):
    """Execute JavaScript in ``driver`` to close known pop-ups and log results."""

    result = driver.execute_script(POPUP_CLOSE_SCRIPT)
    print("닫기 시도 대상:", result)
    return result.get("count", 0)
