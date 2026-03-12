from __future__ import annotations

import applypilot.pipeline as pipeline


def test_run_discover_with_site_filter_only_runs_matching_smart_extract(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        pipeline,
        "console",
        type("DummyConsole", (), {"print": staticmethod(lambda *args, **kwargs: None)})(),
    )

    def _fake_load_sites():
        return [
            {"name": "Lensa", "url": "https://lensa.example", "type": "search"},
            {"name": "Dice", "url": "https://dice.example", "type": "search"},
        ]

    def _fake_run_smart_extract(*, sites, workers):
        captured["sites"] = sites
        captured["workers"] = workers

    monkeypatch.setattr("applypilot.discovery.smartextract.load_sites", _fake_load_sites)
    monkeypatch.setattr("applypilot.discovery.smartextract.run_smart_extract", _fake_run_smart_extract)

    result = pipeline._run_discover(workers=2, site_filter=["Lensa"])

    assert captured["sites"] == [{"name": "Lensa", "url": "https://lensa.example", "type": "search"}]
    assert captured["workers"] == 2
    assert result["jobspy"] == "skipped (site-filter)"
    assert result["workday"] == "skipped (site-filter)"
    assert result["smartextract"] == "ok"
    assert result["greenhouse"] == "skipped (site-filter)"
