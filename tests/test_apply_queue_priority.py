from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from applypilot.apply import launcher
from applypilot.database import close_connection, init_db


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
    conn.execute(
        f"INSERT INTO jobs ({', '.join(cols)}) VALUES ({placeholders})",
        vals,
    )


def test_acquire_job_prioritizes_untried_before_retries(monkeypatch) -> None:
    tmp_root = _make_test_dir()
    db_path = tmp_root / "applypilot.db"

    try:
        conn = init_db(db_path)

        retry_url = "https://example.com/a-retry"
        fresh_url = "https://example.com/z-fresh"

        _insert_job(
            conn,
            retry_url,
            title="Retry Candidate",
            site="Example",
            application_url=retry_url,
            tailored_resume_path="C:/tmp/retry.txt",
            fit_score=7,
            apply_status="failed",
            apply_attempts=1,
        )
        _insert_job(
            conn,
            fresh_url,
            title="Fresh Candidate",
            site="Example",
            application_url=fresh_url,
            tailored_resume_path="C:/tmp/fresh.txt",
            fit_score=7,
            apply_attempts=0,
        )
        conn.commit()

        monkeypatch.setattr(launcher, "get_connection", lambda: conn)
        monkeypatch.setattr(launcher, "_load_blocked", lambda: ([], []))

        job = launcher.acquire_job(min_score=7, worker_id=7)

        assert job is not None
        assert job["url"] == fresh_url

        row = conn.execute(
            "SELECT apply_status, agent_id FROM jobs WHERE url = ?",
            (fresh_url,),
        ).fetchone()
        assert row["apply_status"] == "in_progress"
        assert row["agent_id"] == "worker-7"
    finally:
        close_connection(db_path)
        shutil.rmtree(tmp_root, ignore_errors=True)
