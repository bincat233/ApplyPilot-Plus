from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from typer.testing import CliRunner

import applypilot.cli as cli
import applypilot.database as database
import applypilot.pipeline as pipeline
from applypilot.database import close_connection, init_db


runner = CliRunner()


def _make_test_dir() -> Path:
    root = Path.cwd() / ".test_tmp"
    root.mkdir(parents=True, exist_ok=True)
    path = root / str(uuid4())
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_run_reset_enrich_errors_clears_error_state(monkeypatch) -> None:
    tmp_root = _make_test_dir()
    db_path = tmp_root / "applypilot.db"

    try:
        conn = init_db(db_path)
        conn.execute(
            """
            INSERT INTO jobs (url, detail_scraped_at, detail_error)
            VALUES (?, ?, ?)
            """,
            ("https://example.com/job/1", "2026-03-12T00:00:00+00:00", "timeout"),
        )
        conn.commit()

        monkeypatch.setattr(cli, "_bootstrap", lambda: None)
        monkeypatch.setattr(database, "get_connection", lambda: conn)
        monkeypatch.setattr(pipeline, "run_pipeline", lambda **kwargs: {"errors": {}})

        result = runner.invoke(cli.app, ["run", "enrich", "--reset-enrich-errors", "--dry-run"])

        assert result.exit_code == 0
        row = conn.execute(
            "SELECT detail_scraped_at, detail_error FROM jobs WHERE url = ?",
            ("https://example.com/job/1",),
        ).fetchone()
        assert row["detail_scraped_at"] is None
        assert row["detail_error"] is None
    finally:
        close_connection(db_path)
        shutil.rmtree(tmp_root, ignore_errors=True)
