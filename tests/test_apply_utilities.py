from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from typer.testing import CliRunner

import applypilot.cli as cli
from applypilot.apply import launcher
from applypilot.database import close_connection, init_db


runner = CliRunner()


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


def test_remove_expired_deletes_expired_jobs(monkeypatch) -> None:
    tmp_root = _make_test_dir()
    db_path = tmp_root / "applypilot.db"

    try:
        conn = init_db(db_path)
        _insert_job(conn, "https://example.com/expired-by-status", apply_status="expired")
        _insert_job(conn, "https://example.com/expired-by-error", apply_status="failed", apply_error="expired")
        _insert_job(conn, "https://example.com/keep-captcha", apply_status="failed", apply_error="captcha")
        conn.commit()

        monkeypatch.setattr(launcher, "get_connection", lambda: conn)

        removed = launcher.remove_expired()

        assert removed == 2
        rows = conn.execute("SELECT url FROM jobs ORDER BY url").fetchall()
        assert [row["url"] for row in rows] == ["https://example.com/keep-captcha"]
    finally:
        close_connection(db_path)
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_reset_in_progress_clears_stuck_worker_locks(monkeypatch) -> None:
    tmp_root = _make_test_dir()
    db_path = tmp_root / "applypilot.db"

    try:
        conn = init_db(db_path)
        _insert_job(conn, "https://example.com/stuck", apply_status="in_progress", agent_id="worker-0", apply_attempts=0)
        _insert_job(conn, "https://example.com/failed", apply_status="failed", agent_id=None, apply_attempts=1)
        conn.commit()

        monkeypatch.setattr(launcher, "get_connection", lambda: conn)

        reset = launcher.reset_in_progress()

        assert reset == 1
        rows = conn.execute("SELECT url, apply_status, agent_id FROM jobs ORDER BY url").fetchall()
        row_map = {row["url"]: (row["apply_status"], row["agent_id"]) for row in rows}
        assert row_map["https://example.com/stuck"] == (None, None)
        assert row_map["https://example.com/failed"] == ("failed", None)
    finally:
        close_connection(db_path)
        shutil.rmtree(tmp_root, ignore_errors=True)


def test_apply_remove_expired_cli(monkeypatch) -> None:
    monkeypatch.setattr(cli, "_bootstrap", lambda: None)
    monkeypatch.setattr("applypilot.apply.launcher.remove_expired", lambda: 3)

    result = runner.invoke(cli.app, ["apply", "--remove-expired"])

    assert result.exit_code == 0
    assert "Removed 3 expired job(s)." in result.output


def test_apply_reset_in_progress_cli(monkeypatch) -> None:
    monkeypatch.setattr(cli, "_bootstrap", lambda: None)
    monkeypatch.setattr("applypilot.apply.launcher.reset_in_progress", lambda: 2)

    result = runner.invoke(cli.app, ["apply", "--reset-in-progress"])

    assert result.exit_code == 0
    assert "Reset 2 in-progress job(s)." in result.output
