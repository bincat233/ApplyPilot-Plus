from __future__ import annotations

from applypilot.apply import chrome


def test_is_cdp_ready_returns_false_on_url_error(monkeypatch) -> None:
    def fake_urlopen(url, timeout=0):
        raise chrome.urllib.error.URLError("boom")

    monkeypatch.setattr(chrome.urllib.request, "urlopen", fake_urlopen)

    assert chrome._is_cdp_ready(9222) is False


def test_wait_for_cdp_returns_true_once_endpoint_is_ready(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_ready(port: int, timeout: float = 1.5) -> bool:
        calls["count"] += 1
        return calls["count"] >= 3

    now = {"value": 0.0}

    monkeypatch.setattr(chrome, "_is_cdp_ready", fake_ready)
    monkeypatch.setattr(chrome.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(chrome.time, "time", lambda: now.__setitem__("value", now["value"] + 0.1) or now["value"])

    assert chrome._wait_for_cdp(9222, max_wait_sec=1.0) is True
    assert calls["count"] >= 3
