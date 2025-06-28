"""Utilities for closing pop-up windows during automation."""


POPUP_CLOSE_SCRIPT = """
return (function() {
  let closed = 0;
  // Case A: explicit structure containing STCM230_P1
  const popupAList = Array.from(document.querySelectorAll('[id*="STCM230_P1"]'));
  popupAList.forEach(popup => {
    const closeBtn = popup.querySelector('[id$="btnClose"]');
    if (closeBtn) {
      closeBtn.click();
      closed++;
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
    const closeBtn = div.querySelector('button, div, a');
    if (closeBtn && /닫기|확인/.test(closeBtn.innerText)) {
      closeBtn.click();
      closed++;
    }
  });

  return closed;
})();
"""


def close_popups(driver):
    """Execute JavaScript in ``driver`` to close known pop-ups.

    Parameters
    ----------
    driver : selenium.webdriver.remote.webdriver.WebDriver
        Active WebDriver instance.

    Returns
    -------
    Any
        Result returned from ``driver.execute_script``, typically the number of
        pop-ups closed.
    """

    return driver.execute_script(POPUP_CLOSE_SCRIPT)
