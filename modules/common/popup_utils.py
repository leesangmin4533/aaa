"""Utilities for closing pop-up windows during automation."""


POPUP_CLOSE_SCRIPT = """
return (function () {
  const result = {
    detected: false,
    closed: false,
    reason: "",
    target: null
  };

  // 1. \ube14\ub7ec \uc694\uc18c \uac10\uc9c0
  const allDivs = Array.from(document.querySelectorAll('div'));
  const blurred = allDivs.find(div => {
    const style = window.getComputedStyle(div);
    return style.filter.includes('blur') || style.backdropFilter.includes('blur');
  });

  if (!blurred) {
    result.reason = '\ube14\ub7ec \uc5c6\uc74c';
    return result;
  }

  // \ube14\ub7ec\uac00 \uac10\uc9c0\ub418\uba74 \uc77c\uc2dc \uc911\ub2e8 \uc870\uac74 \ub9dd\uc131
  result.detected = true;

  // 2. \ud31d\uc5c5 \ubd84\uc11d
  const popupCandidates = allDivs.filter(div => {
    const style = window.getComputedStyle(div);
    return (
      style.position === 'fixed' &&
      parseInt(style.zIndex || '0') > 1000 &&
      style.display !== 'none' &&
      style.visibility !== 'hidden'
    );
  });

  for (let popup of popupCandidates) {
    const buttons = popup.querySelectorAll('button, div, a');
    for (let btn of buttons) {
      const text = btn.innerText?.trim();
      const isClickable =
        btn.onclick ||
        btn.getAttribute('role') === 'button' ||
        /btn|nexabutton/.test(btn.className);
      if (isClickable && /(\ub2eb\uae30|\ud655\uc778|\ub2e4\uc2dc \ubcf4\uc9c0 \uc54a\uae30)/.test(text)) {
        try {
          btn.click();
          result.closed = true;
          result.target = text + ' / ' + (btn.id || '[no-id]');
          return result;
        } catch (e) {
          result.reason = '\ubc84\ud2bc \ud074\ub9ad \uc2e4\ud328';
          return result;
        }
      }
    }
  }

  result.reason = '\ud31d\uc5c5 \ubc84\ud2bc \uc5c6\uc74c';
  return result;
})();
"""


def close_popups(driver):
    """Execute JavaScript in ``driver`` to detect and close blur-based pop-ups."""

    return driver.execute_script(POPUP_CLOSE_SCRIPT)
