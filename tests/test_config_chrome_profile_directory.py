from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from applypilot import config
from applypilot.apply import chrome


def _make_test_dir() -> Path:
    root = Path.cwd() / ".test_tmp"
    root.mkdir(parents=True, exist_ok=True)
    path = root / str(uuid4())
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_get_chrome_profile_directory_uses_env_override(monkeypatch) -> None:
    monkeypatch.setenv("CHROME_PROFILE_DIRECTORY", "Profile 42")
    assert config.get_chrome_profile_directory() == "Profile 42"


def test_get_chrome_profile_directory_reads_local_state(monkeypatch) -> None:
    tmp_root = _make_test_dir()
    user_data = tmp_root / "User Data"
    user_data.mkdir(parents=True, exist_ok=True)
    (user_data / "Local State").write_text(
        json.dumps({"profile": {"last_used": "Profile 7"}}),
        encoding="utf-8",
    )

    monkeypatch.delenv("CHROME_PROFILE_DIRECTORY", raising=False)
    monkeypatch.setattr(config, "get_chrome_user_data", lambda: user_data)

    try:
        assert config.get_chrome_profile_directory() == "Profile 7"
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_launch_chrome_uses_selected_profile_directory(monkeypatch) -> None:
    class DummyProc:
        pid = 12345

        @staticmethod
        def poll():
            return 0

    captured: dict[str, list[str]] = {}
    profile_dir = Path("/tmp/fake-chrome-profile")

    def fake_popen(cmd, **kwargs):
        captured["cmd"] = cmd
        return DummyProc()

    monkeypatch.setattr(config, "get_chrome_path", lambda: "/usr/bin/google-chrome-stable")
    monkeypatch.setattr(config, "get_chrome_profile_directory", lambda: "Profile 3")
    monkeypatch.setattr(chrome, "setup_worker_profile", lambda worker_id, profile_directory=None: profile_dir)
    monkeypatch.setattr(chrome, "_kill_on_port", lambda port: None)
    monkeypatch.setattr(chrome, "_suppress_restore_nag", lambda profile_dir, profile_directory=None: None)
    monkeypatch.setattr(chrome, "_wait_for_cdp", lambda port, max_wait_sec=12.0: True)
    monkeypatch.setattr(chrome.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(chrome.time, "sleep", lambda seconds: None)

    proc = chrome.launch_chrome(worker_id=0, port=9555, headless=False)

    assert proc.pid == 12345
    assert f"--user-data-dir={profile_dir}" in captured["cmd"]
    assert "--profile-directory=Profile 3" in captured["cmd"]
