import importlib.util
import pathlib
import sys
import types
import json
import pytest

# minimal fake selenium package
selenium_pkg = types.ModuleType("selenium")
webdriver_pkg = types.ModuleType("selenium.webdriver")
remote_pkg = types.ModuleType("selenium.webdriver.remote")
webdriver_module = types.ModuleType("selenium.webdriver.remote.webdriver")

class WebDriver:
    pass

webdriver_module.WebDriver = WebDriver
remote_pkg.webdriver = webdriver_module
webdriver_pkg.remote = remote_pkg
selenium_pkg.webdriver = webdriver_pkg

sys.modules.setdefault("selenium", selenium_pkg)
sys.modules.setdefault("selenium.webdriver", webdriver_pkg)
sys.modules.setdefault("selenium.webdriver.remote", remote_pkg)
sys.modules.setdefault("selenium.webdriver.remote.webdriver", webdriver_module)

# stub popup util module to avoid selenium dependency
popup_pkg = types.ModuleType("utils.popup_util")

def _noop(*a, **k):
    pass

popup_pkg.close_nexacro_popups = _noop
popup_pkg.close_focus_popup = _noop
popup_pkg.ensure_focus_popup_closed = _noop
popup_pkg.close_popups_after_delegate = _noop
sys.modules["utils.popup_util"] = popup_pkg

# load login_bgf module from file
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
_spec = importlib.util.spec_from_file_location(
    "login.login_bgf",
    pathlib.Path(__file__).resolve().parents[1] / "login" / "login_bgf.py",
)
login_bgf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(login_bgf)


def test_load_credentials_from_env(monkeypatch):
    monkeypatch.setenv("BGF_USER_ID", "user")
    monkeypatch.setenv("BGF_PASSWORD", "pw")
    creds = login_bgf.load_credentials(
        {"id": "BGF_USER_ID", "password": "BGF_PASSWORD"}
    )
    assert creds == {"id": "user", "password": "pw"}


def test_load_credentials_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("BGF_USER_ID", raising=False)
    monkeypatch.delenv("BGF_PASSWORD", raising=False)
    (tmp_path / ".env").write_text(
        "BGF_USER_ID=env_user\nBGF_PASSWORD=env_pw\n", encoding="utf-8"
    )
    monkeypatch.setattr(login_bgf, "ROOT_DIR", tmp_path)
    creds = login_bgf.load_credentials(
        {"id": "BGF_USER_ID", "password": "BGF_PASSWORD"}
    )
    assert creds == {"id": "env_user", "password": "env_pw"}
def test_load_credentials_failure_missing_env(tmp_path, monkeypatch):
    monkeypatch.delenv("BGF_USER_ID", raising=False)
    monkeypatch.delenv("BGF_PASSWORD", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError):
        login_bgf.load_credentials(
            {"id": "BGF_USER_ID", "password": "BGF_PASSWORD"}
        )


def test_login_bgf_invokes_popup_closer(monkeypatch):
    class DummyDriver:
        def __init__(self):
            self.executed = []

        def get(self, url):
            self.url = url

        def execute_script(self, script):
            self.executed.append(script)
            return True

    called = {}

    def _close(driver, timeout=15):
        called["called"] = True

    sys.modules["utils.popup_util"] = popup_pkg
    popup_pkg.close_popups_after_delegate = _close

    def dummy_wait(driver, timeout):
        class _W:
            def until(self, func):
                return func(driver)

        return _W()

    monkeypatch.setattr(login_bgf, "WebDriverWait", dummy_wait)
    monkeypatch.setenv("BGF_USER_ID", "user")
    monkeypatch.setenv("BGF_PASSWORD", "pw")

    result = login_bgf.login_bgf(
        DummyDriver(), {"id": "BGF_USER_ID", "password": "BGF_PASSWORD"}
    )

    assert result is True
    assert called.get("called") is True
