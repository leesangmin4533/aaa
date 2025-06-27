"""Utility for capturing SSV data from Chrome DevTools Protocol."""
from pathlib import Path


def extract_ssv_from_cdp(driver, keyword: str, save_to: str) -> None:
    """Placeholder implementation to save a matching network response.

    This function enables network logging via CDP and scans received responses
    for ``keyword`` in the request URL. When found, it saves the response body
    to ``save_to``. The logic is simplified and may need adjustments for real
    environments.
    """
    try:
        driver.execute_cdp_cmd("Network.enable", {})
    except Exception:
        return

    def on_response(event):
        request_id = event.get("requestId")
        try:
            info = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
        except Exception:
            return
        url = event.get("response", {}).get("url", "")
        if keyword in url:
            Path(save_to).parent.mkdir(parents=True, exist_ok=True)
            with open(save_to, "w", encoding="utf-8") as f:
                f.write(info.get("body", ""))

    driver.add_listener("Network.loadingFinished", on_response)
