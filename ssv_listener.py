"""Utility for capturing SSV data from Chrome DevTools Protocol."""
import json
import time
from pathlib import Path


def extract_ssv_from_cdp(driver, keyword: str, save_to: str) -> None:
    """Save the body of a network response containing ``keyword`` in the URL.

    The function polls Chrome performance logs for ``Network.responseReceived``
    events and retrieves the response body via CDP. It waits up to 5 seconds for
    a matching request.
    """

    try:
        driver.execute_cdp_cmd("Network.enable", {})
    except Exception:
        print("\u274c CDP 네트워크 활성화 실패")
        return

    matched_body: str | None = None
    timeout = time.time() + 5

    while time.time() < timeout:
        try:
            logs = driver.get_log("performance")
        except Exception:
            logs = []

        for entry in logs:
            try:
                message = json.loads(entry["message"])["message"]
            except Exception:
                continue
            if (
                message.get("method") == "Network.responseReceived"
                and keyword in message.get("params", {}).get("response", {}).get("url", "")
            ):
                request_id = message["params"].get("requestId")
                if not request_id:
                    continue
                try:
                    body = driver.execute_cdp_cmd(
                        "Network.getResponseBody", {"requestId": request_id}
                    )
                    matched_body = body.get("body", "")
                    break
                except Exception:
                    continue
        if matched_body:
            break
        time.sleep(0.25)

    if matched_body is not None:
        Path(save_to).parent.mkdir(parents=True, exist_ok=True)
        with open(save_to, "w", encoding="utf-8") as f:
            f.write(matched_body)
        print(f"\u2705 SSV 저장 완료: {save_to}")
    else:
        print(f"\u26a0\ufe0f 5초 내 selDetailSearch 응답 감지 실패: {keyword}")
