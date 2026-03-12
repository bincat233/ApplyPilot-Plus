from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from applypilot.database import close_connection, get_jobs_by_stage, get_stats, init_db


def _make_test_dir() -> Path:
    root = Path.cwd() / ".test_tmp"
    root.mkdir(parents=True, exist_ok=True)
    path = root / str(uuid4())
    path.mkdir(parents=True, exist_ok=True)
    return path


def _insert_job(conn, url: str, **fields) -> None:
    cols = ["url", *fields.keys()]
    vals = [url, *fields.values()]
    placeholders = ", ".join("?" for _ in cols)
    conn.execute(f"INSERT INTO jobs ({', '.join(cols)}) VALUES ({placeholders})", vals)


def test_pending_apply_filters_out_ineligible_jobs() -> None:
    tmp_root = _make_test_dir()
    db_path = tmp_root / "applypilot.db"

    try:
        conn = init_db(db_path)
        common = {
            "detail_scraped_at": "2026-03-01T00:00:00+00:00",
            "full_description": "Job details",
            "tailored_resume_path": str(tmp_root / "resume.txt"),
            "application_url": "https://example.com/apply",
        }

        _insert_job(conn, "https://example.com/eligible", fit_score=9, apply_status=None, apply_attempts=0, **common)
        _insert_job(conn, "https://example.com/failed-retry", fit_score=8, apply_status="failed", apply_attempts=1, **common)
        _insert_job(conn, "https://example.com/in-progress", fit_score=9, apply_status="in_progress", apply_attempts=0, **common)
        _insert_job(conn, "https://example.com/too-many-attempts", fit_score=9, apply_status="failed", apply_attempts=3, **common)
        _insert_job(conn, "https://example.com/low-score", fit_score=6, apply_status=None, apply_attempts=0, **common)
        conn.commit()

        stats = get_stats(conn)
        pending = get_jobs_by_stage(conn=conn, stage="pending_apply", limit=20)

        assert stats["ready_to_apply"] == 2
        assert [job["url"] for job in pending] == [
            "https://example.com/eligible",
            "https://example.com/failed-retry",
        ]
    finally:
        close_connection(db_path)
        shutil.rmtree(tmp_root, ignore_errors=True)
