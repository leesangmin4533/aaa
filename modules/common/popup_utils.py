"""Utilities for closing pop-up windows during automation."""


POPUP_CLOSE_SCRIPT = """
return (function () {
  const result = {
    detected: false,
    closed: false,
    reason: "",
    target: null
  };

  // 1. \ud31d\uc5c5 \ud3ec\ud568 \uac10\uc9c0 (z-index+fixed+\ud06c\uae30)
  const allDivs = Array.from(document.querySelectorAll('div'));
  const popupCandidates = allDivs.filter(div => {
    const style = window.getComputedStyle(div);
    return (
      style.position === 'fixed' &&
      parseInt(style.zIndex || '0') > 1000 &&
      div.offsetWidth > 300 &&
      div.offsetHeight > 200 &&
      style.display !== 'none' &&
      style.visibility !== 'hidden'
    );
  });

  if (popupCandidates.length === 0) {
    result.reason = '\ud31d\uc5c5 \uc5c6\uc74c';
    return result;
  }

  result.detected = true;

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
    """Execute JavaScript in ``driver`` to detect and close pop-ups using z-index
    and size-based criteria."""

    return driver.execute_script(POPUP_CLOSE_SCRIPT)
