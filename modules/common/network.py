import json
from pathlib import Path
import time

MODULE_NAME = "network"


def log(step: str, msg: str) -> None:
    print(f"\u25b6 [{MODULE_NAME} > {step}] {msg}")


def extract_ssv_from_cdp(driver, keyword: str, save_to: str) -> None:
    """
    Listen for a network response matching `keyword` in URL,
    then save response body to `save_to`.
    """

    try:
        driver.execute_cdp_cmd("Network.enable", {})
    except Exception:
        log("enable_cdp", "CDP 네트워크 활성화 실패")
        return

    matched_body = None
    timeout = time.time() + 5  # 최대 5초 대기

    while time.time() < timeout:
        logs = driver.get_log("performance")
        for entry in logs:
            try:
                message = json.loads(entry["message"])["message"]
                if (
                    message["method"] == "Network.responseReceived"
                    and keyword in message.get("params", {}).get("response", {}).get("url", "")
                ):
                    request_id = message["params"]["requestId"]
                    body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                    matched_body = body.get("body", "")
                    break
            except Exception:
                continue
        if matched_body:
            break
        time.sleep(0.25)

    if matched_body:
        Path(save_to).parent.mkdir(parents=True, exist_ok=True)
        with open(save_to, "w", encoding="utf-8") as f:
            f.write(matched_body)
        log("save_ssv", f"SSV 저장 완료: {save_to}")
    else:
        log("wait_response", f"5초 내 selDetailSearch 응답 감지 실패: {keyword}")
