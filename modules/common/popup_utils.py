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

  const clickedIds = new Set();

  popupBList.forEach(div => {
    const buttons = Array.from(div.querySelectorAll('button, a, div')).filter(el => {
      const txt = el.innerText.trim();
      const isClickable =
        typeof el.onclick === 'function' ||
        /nexabutton/i.test(el.className);

      const isUnique = el.id && !clickedIds.has(el.id);

      return isClickable && isUnique && /(닫기|확인|다시 보지 않기)/.test(txt);
    });

    buttons.forEach(btn => {
      try {
        btn.click();
        if (typeof btn.onclick === 'function') {
          btn.onclick();
        } else {
          const evt = new MouseEvent('click', { bubbles: true, cancelable: true });
          btn.dispatchEvent(evt);
        }
        clickedIds.add(btn.id);
        closed++;
        closedIds.push(`${btn.innerText} / ${btn.id || '[no-id]'}`);
      } catch (e) {
        closedIds.push(`[실패] ${btn.innerText} / ${btn.id || '[no-id]'}`);
      }
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
