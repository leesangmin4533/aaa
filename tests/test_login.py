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
sys.modules.setdefault("utils.popup_util", popup_pkg)

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
    creds = login_bgf.load_credentials()
    assert creds == {"id": "user", "password": "pw"}


def test_load_credentials_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("BGF_USER_ID", raising=False)
    monkeypatch.delenv("BGF_PASSWORD", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "BGF_USER_ID=env_user\nBGF_PASSWORD=env_pw\n", encoding="utf-8"
    )
    creds = login_bgf.load_credentials()
    assert creds == {"id": "env_user", "password": "env_pw"}


def test_load_credentials_from_json(tmp_path, monkeypatch):
    monkeypatch.delenv("BGF_USER_ID", raising=False)
    monkeypatch.delenv("BGF_PASSWORD", raising=False)
    monkeypatch.chdir(tmp_path)
    data = {"id": "juser", "password": "jpw"}
    cred_file = tmp_path / "cred.json"
    cred_file.write_text(json.dumps(data), encoding="utf-8")
    creds = login_bgf.load_credentials(str(cred_file))
    assert creds == data


def test_load_credentials_failure_no_source(tmp_path, monkeypatch):
    monkeypatch.delenv("BGF_USER_ID", raising=False)
    monkeypatch.delenv("BGF_PASSWORD", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError):
        login_bgf.load_credentials()


def test_load_credentials_failure_invalid_json(tmp_path, monkeypatch):
    monkeypatch.delenv("BGF_USER_ID", raising=False)
    monkeypatch.delenv("BGF_PASSWORD", raising=False)
    monkeypatch.chdir(tmp_path)
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("not json", encoding="utf-8")
    with pytest.raises(RuntimeError):
        login_bgf.load_credentials(str(bad_file))
