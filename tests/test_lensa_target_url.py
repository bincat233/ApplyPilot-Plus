from __future__ import annotations

from applypilot.discovery.smartextract import build_scrape_targets, load_sites


def test_lensa_targets_use_current_job_search_route() -> None:
    search_cfg = {
        "queries": [{"query": "VP of Information Technology"}],
        "locations": [{"location": "Remote", "remote": True}],
    }

    sites = [site for site in load_sites() if site.get("name") == "Lensa"]

    targets = build_scrape_targets(sites=sites, search_cfg=search_cfg)

    assert targets == [
        {
            "name": "Lensa",
            "url": (
                "https://lensa.com/talent/job-opportunities"
                "?flow=comingFromLandingPage&job-title=VP+of+Information+Technology&remote_jobs=only"
            ),
            "query": "VP of Information Technology",
        }
    ]
