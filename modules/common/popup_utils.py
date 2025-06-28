"""Utilities for closing pop-up windows during automation."""


POPUP_CLOSE_SCRIPT = """
return (function() {
  let closed = 0;
  let closedIds = [];

  // Case A: explicit structure containing STCM230_P1
  const popupAList = Array.from(document.querySelectorAll('[id*="STCM230_P1"]'));
  popupAList.forEach(popup => {
    const closeBtn = popup.querySelector('[id$="btnClose"]');
    if (closeBtn) {
      console.log('닫기 대상:', closeBtn.innerText, closeBtn.id, closeBtn.className);
      closeBtn.click();
      closed++;
      closedIds.push(closeBtn.id || '[no-id]');
    }
  });

  // Case B: generic pattern based structure
  const popupBList = Array.from(document.querySelectorAll('div')).filter(div => {
    const style = window.getComputedStyle(div);
    const isVisible = style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    const isCentered = style.position === 'fixed' || style.position === 'absolute';
    const isLarge = div.offsetWidth > 300 && div.offsetHeight > 200;
    return isVisible && isCentered && isLarge;
  });

  popupBList.forEach(div => {
    const buttons = Array.from(div.querySelectorAll('button, a, div')).filter(el => {
      const txt = el.innerText.trim();
      const isClickable = el.onclick || el.getAttribute('role') === 'button' || el.className.includes('btn') || el.className.includes('nexabutton');
      return isClickable && /(닫기|확인|다시 보지 않기)/.test(txt);
    });

    buttons.forEach(btn => {
      btn.click();
      closed++;
      closedIds.push(`${btn.innerText} / ${btn.id || '[no-id]'}`);
    });
  });

  return { count: closed, targets: closedIds };
})();
"""


def close_popups(driver):
    """Execute JavaScript in ``driver`` to close known pop-ups and log results."""

    result = driver.execute_script(POPUP_CLOSE_SCRIPT)
    print("닫기 시도 대상:", result)
    return result.get("count", 0)
