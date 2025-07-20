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


def execute_collect_past7days(driver: WebDriver) -> dict:
    """Execute the collectPast7Days function asynchronously."""
    return driver.execute_async_script(
        """
const callback = arguments[arguments.length - 1];
if (!window.automation || typeof window.automation.collectPast7Days !== 'function') {
  callback({ success: false, message: 'collectPast7Days not defined' });
  return;
}
window.automation.collectPast7Days()
  .then(res => callback({ success: true, message: res }))
  .catch(err => callback({ success: false, message: window.automation.error || err.message }));
"""
    )
