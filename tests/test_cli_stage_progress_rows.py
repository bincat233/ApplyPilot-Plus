from __future__ import annotations

from applypilot.cli import _build_stage_progress_rows


def test_build_stage_progress_rows_shapes_counts() -> None:
    stats = {
        "total": 12,
        "pending_detail": 5,
        "scored": 4,
        "unscored": 3,
        "tailored": 3,
        "untailored_eligible": 2,
        "with_cover_letter": 2,
        "ready_to_apply": 2,
        "applied": 1,
    }

    rows = _build_stage_progress_rows(stats)

    assert rows == [
        ("Enrichment", 12, 5, 7),
        ("Scoring", 7, 3, 4),
        ("Tailoring (7+)", 5, 2, 3),
        ("Cover Letters", 3, 1, 2),
        ("PDF Conversion", 3, 1, 2),
        ("Applications", 2, 1, 1),
    ]
