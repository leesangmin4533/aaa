from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time
from typing import Any

from .log_util import get_logger

log = get_logger(__name__)

def close_all_modals(driver: WebDriver, max_attempts: int = 5) -> int:
    """Closes all modal popups by simulating mouse events on common close buttons.

    This function iteratively searches for and simulates mouse events on elements
    that are likely to close modal dialogs, such as buttons with '닫기', '확인',
    '취소', or 'x' characters, or specific IDs like 'btn_topClose', 'btnClose'.
    It continues until no more such buttons are found or the maximum number of
    attempts is reached.

    Args:
        driver: The Selenium WebDriver instance.
        max_attempts: The maximum number of times to loop and close popups.

    Returns:
        The total number of popups closed.
    """
    closed_count = 0
    for attempt in range(max_attempts):
        log.info(f"Attempt {attempt + 1}/{max_attempts} to find and close popups.", extra={'tag': 'modal_closer'})
        found_and_closed_popup = False

        # JavaScript to find and click elements by simulating mouse events
        js_script = """
        function simulateClick(element) {
            const rect = element.getBoundingClientRect();
            const centerX = rect.left + rect.width / 2;
            const centerY = rect.top + rect.height / 2;

            const eventOptions = {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: centerX,
                clientY: centerY
            };

            element.dispatchEvent(new MouseEvent('mousedown', eventOptions));
            element.dispatchEvent(new MouseEvent('mouseup', eventOptions));
            element.dispatchEvent(new MouseEvent('click', eventOptions));
            return true;
        }

        const textSelectors = [
            '닫기', '확인', '취소', 'Close', 'OK', 'Cancel', '×', 'X'
        ];
        const idSelectors = [
            'btn_topClose',
            'btnClose',
            'mainframe.HFrameSet00.VFrameSet00.FrameSet.WorkFrame.STZZ120_P0.form.btn_close',
            'mainframe.HFrameSet00.VFrameSet00.FrameSet.WorkFrame.STZZ120_P0.form.btn_closeTop',
            'mainframe.HFrameSet00.VFrameSet00.TopFrame.STZZ210_P0.form.btn_enter'
        ];
        const classSelectors = [
            'close', 'popup-close'
        ];
        const ariaLabelSelectors = [
            'Close'
        ];

        let clicked = false;

        // Search by ID
        for (const id of idSelectors) {
            const element = document.getElementById(id);
            if (element && element.offsetParent !== null) {
                const style = window.getComputedStyle(element);
                if (style.display !== 'none' && style.visibility !== 'hidden') {
                    if (simulateClick(element)) {
                        clicked = true;
                        return clicked;
                    }
                }
            }
        }

        // Search by text content
        for (const text of textSelectors) {
            const elements = document.querySelectorAll('button, a, div'); // Search common elements for text
            for (const element of elements) {
                const style = window.getComputedStyle(element);
                if (style.display !== 'none' && style.visibility !== 'hidden' && element.offsetParent !== null) {
                    if (element.innerText && element.innerText.trim() === text) {
                        if (simulateClick(element)) {
                            clicked = true;
                            return clicked;
                        }
                    }
                }
            }
        }

        // Search by class name
        for (const cls of classSelectors) {
            const elements = document.querySelectorAll('[class*="' + cls + '"]');
            for (const element of elements) {
                const style = window.getComputedStyle(element);
                if (style.display !== 'none' && style.visibility !== 'hidden' && element.offsetParent !== null) {
                    if (simulateClick(element)) {
                        clicked = true;
                        return clicked;
                    }
                }
            }
        }

        // Search by aria-label
        for (const label of ariaLabelSelectors) {
            const elements = document.querySelectorAll('[aria-label*="' + label + '"]');
            for (const element of elements) {
                const style = window.getComputedStyle(element);
                if (style.display !== 'none' && style.visibility !== 'hidden' && element.offsetParent !== null) {
                    if (simulateClick(element)) {
                        clicked = true;
                        return clicked;
                    }
                }
            }
        }

        return clicked;
        """
        try:
            # Execute the JavaScript to find and click a popup button
            clicked_a_popup = driver.execute_script(js_script)
            if clicked_a_popup:
                log.info("Successfully simulated click on a popup close element.", extra={'tag': 'modal_closer'})
                closed_count += 1
                found_and_closed_popup = True
                time.sleep(2)  # Give time for the popup to disappear
            else:
                log.info("No more popups found in this attempt.", extra={'tag': 'modal_closer'})
                break # Exit the loop if no popups were found and closed

        except Exception as e:
            log.error(f"An unexpected error occurred during JavaScript execution: {e}", extra={'tag': 'modal_closer'})
            break
    
    log.info(f"Finished popup closing process. Total closed: {closed_count}", extra={'tag': 'modal_closer'})
    return closed_count


def ensure_focus_popup_closed(driver: WebDriver, timeout: float = 5.0, stable_time: float = 0.5) -> None:
    """Close focus popup by sending ENTER until it disappears."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            popup = driver.find_element(By.XPATH, "//*")
            if not popup.is_displayed():
                return
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            time.sleep(stable_time)
        except Exception:
            break


def close_popups_after_delegate(driver: Any, timeout: int = 15) -> int:
    """Find and close all popups within a given timeout.

    This function repeatedly finds and closes popups until no more are found
    or the timeout is reached.
    """
    from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    popup_selectors = [
        "div.div_pop_wrap[style*='display: block']",
        "div.div_pop_wrap[style*='display:flex']",
        "div.pop_wrap[style*='display: block']",
    ]
    close_button_selectors = ["a.btn_pop_close", "button.btn_pop_close"]

    closed_count = 0
    start_time = time.time()

    while time.time() - start_time < timeout:
        popups_found_in_iteration = False
        for popup_selector in popup_selectors:
            try:
                popups = driver.find_elements(By.CSS_SELECTOR, popup_selector)
                for popup in popups:
                    if not popup.is_displayed():
                        continue

                    for btn_selector in close_button_selectors:
                        try:
                            close_button = popup.find_element(By.CSS_SELECTOR, btn_selector)
                            if close_button.is_displayed() and close_button.is_enabled():
                                driver.execute_script("arguments[0].click();", close_button)
                                log.info("Successfully clicked a popup close button.")

                                # Wait for the popup to become stale (disappear)
                                WebDriverWait(driver, 2).until(
                                    EC.staleness_of(popup)
                                )

                                closed_count += 1
                                popups_found_in_iteration = True
                                break  # Move to the next popup
                        except StaleElementReferenceException:
                            # Popup was closed by a previous action, which is fine.
                            popups_found_in_iteration = True
                            break
                        except Exception:
                            # Other exceptions (e.g., button not found) are ignored
                            pass
                    if popups_found_in_iteration:
                        break # Re-scan for all popups from the start
            except StaleElementReferenceException:
                 # The popup disappeared while we were iterating, which is a good thing.
                popups_found_in_iteration = True
                break
            except Exception as e:
                log.warning(f"Error finding popups with selector {popup_selector}: {e}")
        
        # If we went through a full loop without finding any popups, we can exit early.
        if not popups_found_in_iteration:
            break
        
        time.sleep(0.2) # Small delay to prevent a tight loop

    log.info(f"Finished popup closing process. Total closed: {closed_count}")
    return closed_count
