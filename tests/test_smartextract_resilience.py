from __future__ import annotations

import applypilot.discovery.smartextract as smartextract


def test_run_one_site_returns_error_when_intelligence_collection_times_out(monkeypatch) -> None:
    def _raise_timeout(url: str, headless: bool = True) -> dict:
        raise TimeoutError("Timeout 30000ms exceeded.")

    monkeypatch.setattr(smartextract, "collect_page_intelligence", _raise_timeout)

    result = smartextract._run_one_site("Lensa", "https://lensa.com/jobs?q=vp")

    assert result["name"] == "Lensa"
    assert result["status"] == "INTEL_ERROR"
    assert "Timeout 30000ms exceeded." in result["error"]


def test_run_all_continues_when_one_worker_raises(monkeypatch) -> None:
    class _Conn:
        def execute(self, *args, **kwargs):
            return self

        def fetchone(self):
            return [0]

        def commit(self) -> None:
            return None

    targets = [
        {"name": "Broken", "url": "https://example.com/broken", "query": None},
        {"name": "Healthy", "url": "https://example.com/healthy", "query": None},
    ]

    def _fake_run_one_site(name: str, url: str, query=None) -> dict:
        if name == "Broken":
            raise TimeoutError("Timeout 30000ms exceeded.")
        return {
            "name": name,
            "status": "PASS",
            "strategy": "api_response",
            "total": 1,
            "titles": 1,
            "jobs": [{"url": "https://jobs.example.com/1", "title": "VP of IT", "location": "Remote"}],
        }

    monkeypatch.setattr(smartextract, "init_db", lambda: _Conn())
    monkeypatch.setattr(smartextract, "get_stats", lambda conn: {"total": 0, "pending_detail": 0})
    monkeypatch.setattr(smartextract, "_run_one_site", _fake_run_one_site)

    result = smartextract._run_all(targets, accept_locs=[], reject_locs=[], workers=2)

    assert result["total"] == 2
    assert result["passed"] == 1
    assert result["total_new"] == 1
