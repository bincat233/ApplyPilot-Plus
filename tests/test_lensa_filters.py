from __future__ import annotations

import applypilot.discovery.smartextract as smartextract


def test_filter_lensa_jobs_drops_low_salary_below_threshold() -> None:
    jobs = [
        {
            "title": "VP of Information Technology",
            "salary": "$143K-$174K / yr. (est.)",
            "description": "Executive IT leadership role.",
            "location": "Remote, Remote",
            "url": "https://example.com/1",
        }
    ]

    filtered = smartextract._filter_lensa_jobs(jobs, "VP of Information Technology")

    assert filtered == []


def test_filter_lensa_jobs_keeps_low_salary_gig_and_fractional_roles() -> None:
    jobs = [
        {
            "title": "Fractional VP of Information Technology",
            "salary": "$90K-$110K / yr. (est.)",
            "description": "Part-time fractional technology leadership engagement.",
            "location": "Remote, Remote",
            "url": "https://example.com/1",
        }
    ]

    filtered = smartextract._filter_lensa_jobs(jobs, "VP of Information Technology")

    assert len(filtered) == 1


def test_filter_lensa_jobs_drops_hybrid_roles_even_when_location_contains_remote() -> None:
    jobs = [
        {
            "title": "VP of Information Technology",
            "salary": "$180K-$220K / yr. (est.)",
            "description": "Hybrid role with regular in-office collaboration.",
            "location": "Remote / Hybrid",
            "url": "https://example.com/1",
        }
    ]

    filtered = smartextract._filter_lensa_jobs(jobs, "VP of Information Technology")

    assert filtered == []


def test_filter_lensa_jobs_drops_noisy_title_mismatch() -> None:
    jobs = [
        {
            "title": "Technology Alliances Manager",
            "salary": "$180K-$220K / yr. (est.)",
            "description": "Partnership role for channel alliances.",
            "location": "Remote, Remote",
            "url": "https://example.com/1",
        }
    ]

    filtered = smartextract._filter_lensa_jobs(jobs, "VP of Information Technology")

    assert filtered == []
