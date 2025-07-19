from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import time

from .log_util import create_logger

log = create_logger("popup_util")

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
        log("modal_closer", "INFO", f"Attempt {attempt + 1}/{max_attempts} to find and close popups.")
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
            'btn_topClose', 'btnClose'
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
                log("modal_closer", "INFO", "Successfully simulated click on a popup close element.")
                closed_count += 1
                found_and_closed_popup = True
                time.sleep(1)  # Give time for the popup to disappear
            else:
                log("modal_closer", "INFO", "No more popups found in this attempt.")
                break # Exit the loop if no popups were found and closed

        except Exception as e:
            log("modal_closer", "ERROR", f"An unexpected error occurred during JavaScript execution: {e}")
            break
    
    log("modal_closer", "INFO", f"Finished popup closing process. Total closed: {closed_count}")
    return closed_count