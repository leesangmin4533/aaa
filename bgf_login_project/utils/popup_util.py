from selenium.webdriver.remote.webdriver import WebDriver

from .log_util import create_logger

log = create_logger("popup_util")


def close_nexacro_popups(driver: WebDriver) -> None:
    """Detect and close popups inside a Nexacro application."""
    js = """
try {
    let app = nexacro.getApplication();
    let targets = [];

    // 기존에 확인된 영역 추가
    targets.push(app.mainframe.HFrameSet00.frames?.[0]?.form);
    targets.push(app.mainframe.HFrameSet00?.VFrameSet00?.FrameSet?.WorkFrame?.form);

    // VFrameSet00 내부 프레임 순회하여 form 수집
    let vfs = app.mainframe.HFrameSet00?.VFrameSet00;
    if (vfs?.frames) {
        for (let i = 0; i < vfs.frames.length; i++) {
            let f = vfs.frames[i];
            if (f?.form) targets.push(f.form);
        }
    }

    for (let form of targets) {
        if (!form) continue;
        for (let name in form.all) {
            let comp = form.all[name];
            if (
                (comp instanceof nexacro.Div ||
                 comp instanceof nexacro.PopupDiv ||
                 comp instanceof nexacro.ChildFrame) &&
                comp.visible
            ) {
                if (typeof comp.set_visible === "function") {
                    comp.set_visible(false);
                } else if (typeof comp.close === "function") {
                    comp.close();
                } else if (comp.btn_close && typeof comp.btn_close.click === "function") {
                    comp.btn_close.click();
                }
            }
        }
    }
    return 'ok';
} catch (e) {
    return 'error: ' + e.toString();
}
"""
    try:
        result = driver.execute_script(js)
        log("close", "INFO", f"팝업 처리 결과: {result}")
    except Exception as e:
        log("close", "ERROR", f"스크립트 실행 실패: {e}")
