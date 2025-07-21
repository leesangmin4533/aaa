from __future__ import annotations

from pathlib import Path
try:
    from selenium.webdriver.remote.webdriver import WebDriver
except Exception:  # pragma: no cover - when selenium is unavailable
    class WebDriver:  # type: ignore
        pass


def load_collect_past7days(driver: WebDriver, scripts_dir: Path | None = None) -> None:
    """Load the collectPast7Days function onto the page."""
    scripts_dir = scripts_dir or Path(__file__).resolve().parents[1] / "scripts"
    path = scripts_dir / "auto_collect_past_7days.js"
    with open(path, "r", encoding="utf-8") as f:
        driver.execute_script(f.read())


def execute_collect_single_day_data(driver: WebDriver, date_str: str) -> dict:
    """Execute the collectSingleDayData function asynchronously for a given date."""
    return driver.execute_async_script(
        """
const callback = arguments[arguments.length - 1];
const dateStr = arguments[0];
if (!window.automation || typeof window.automation.collectSingleDayData !== 'function') {
  callback({ success: false, message: 'collectSingleDayData not defined' });
  return;
}
window.automation.collectSingleDayData(dateStr)
  .then(res => callback(res))
  .catch(err => callback({ success: false, message: window.automation.error || err.message }));
""", date_str
    )
