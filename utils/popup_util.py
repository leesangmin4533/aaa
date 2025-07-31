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
    """Find and close all popups within a given timeout using a robust JS script.

    This function repeatedly polls and executes a JavaScript snippet to find and
    click any popup close buttons until the timeout is reached.
    """
    closed_count = 0
    start_time = time.time()

    js_script = """
    function simulateClick(element) {
        const rect = element.getBoundingClientRect();
        const eventOptions = {
            bubbles: true, cancelable: true, view: window,
            clientX: rect.left + rect.width / 2, clientY: rect.top + rect.height / 2
        };
        element.dispatchEvent(new MouseEvent('mousedown', eventOptions));
        element.dispatchEvent(new MouseEvent('mouseup', eventOptions));
        element.dispatchEvent(new MouseEvent('click', eventOptions));
        return true;
    }

    const textSelectors = ['닫기', '확인', '취소', 'Close', 'OK', 'Cancel', '×', 'X'];
    const idSelectors = [
        'btn_topClose', 'btnClose',
        'mainframe.HFrameSet00.VFrameSet00.FrameSet.WorkFrame.STZZ120_P0.form.btn_close',
        'mainframe.HFrameSet00.VFrameSet00.FrameSet.WorkFrame.STZZ120_P0.form.btn_closeTop',
        'mainframe.HFrameSet00.VFrameSet00.TopFrame.STZZ210_P0.form.btn_enter'
    ];
    const classSelectors = ['close', 'popup-close', 'btn_pop_close'];

    for (const id of idSelectors) {
        const el = document.getElementById(id);
        if (el && el.offsetParent !== null) return simulateClick(el);
    }
    for (const text of textSelectors) {
        const elems = document.querySelectorAll('button, a, div');
        for (const el of elems) {
            if (el.innerText && el.innerText.trim() === text && el.offsetParent !== null) {
                return simulateClick(el);
            }
        }
    }
    for (const cls of classSelectors) {
        const elems = document.querySelectorAll('.' + cls);
        for (const el of elems) {
            if (el.offsetParent !== null) return simulateClick(el);
        }
    }
    return false;
    """

    log.info("Starting to poll for popups...")
    while time.time() - start_time < timeout:
        try:
            was_popup_closed = driver.execute_script(js_script)
            if was_popup_closed:
                log.info("Found and closed a popup.")
                closed_count += 1
                # If we closed one, immediately check for another one.
                time.sleep(0.5)
            else:
                # If no popup was found, wait a bit before trying again.
                time.sleep(0.5)
        except Exception as e:
            log.error(f"An error occurred during popup closing script: {e}")
            # Stop on error to avoid flooding logs
            break
    
    log.info(f"Finished popup closing process. Total closed: {closed_count}")
    return closed_count
