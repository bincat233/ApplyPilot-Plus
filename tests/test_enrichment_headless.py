from __future__ import annotations

import applypilot.enrichment.detail as detail


def test_run_enrichment_passes_headless_to_detail_scraper(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Conn:
        def execute(self, *args, **kwargs):
            return self

        def fetchone(self):
            return [0]

        def close(self) -> None:
            return None

    monkeypatch.setattr(detail, "init_db", lambda: _Conn())
    monkeypatch.setattr(detail, "resolve_all_urls", lambda conn: {"resolved": 0, "already_absolute": 0, "failed": 0})
    monkeypatch.setattr(
        detail,
        "_run_detail_scraper",
        lambda conn, max_per_site, workers, headless: captured.update({
            "max_per_site": max_per_site,
            "workers": workers,
            "headless": headless,
        }) or {"processed": 0, "ok": 0, "partial": 0, "error": 0},
    )

    stats = detail.run_enrichment(limit=5, workers=2, headless=False)

    assert stats["processed"] == 0
    assert captured == {"max_per_site": 5, "workers": 2, "headless": False}
