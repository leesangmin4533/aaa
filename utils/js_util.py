from __future__ import annotations

from pathlib import Path

try:
    from selenium.webdriver.remote.webdriver import WebDriver
except ImportError:
    WebDriver = None


def execute_collect_single_day_data(driver: WebDriver, date_str: str) -> dict:
    """
    Executes the runCollectionForDate function from the loaded JS library.

    This function is asynchronous and waits for the JavaScript to complete.
    """
    script = """
    const callback = arguments[arguments.length - 1];
    const dateStr = arguments[0];
    
    if (!window.automation || typeof window.automation.runCollectionForDate !== 'function') {
        return callback({ 
            success: false, 
            message: 'window.automation.runCollectionForDate function not found. Make sure nexacro_automation_library.js is loaded.' 
        });
    }

    // The JS function is asynchronous, so we can await it.
    window.automation.runCollectionForDate(dateStr)
        .then(() => {
            callback({
                success: true,
                data: window.automation.parsedData,
                error: window.automation.error
            });
        })
        .catch(err => {
            callback({
                success: false,
                message: window.automation.error || err.message
            });
        });
    """
    return driver.execute_async_script(script, date_str)