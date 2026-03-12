from __future__ import annotations

from typer.testing import CliRunner

import applypilot.cli as cli
import applypilot.pipeline as pipeline


runner = CliRunner()


def test_run_show_browser_disables_headless(monkeypatch) -> None:
    monkeypatch.setattr(cli, "_bootstrap", lambda: None)
    captured: dict[str, object] = {}

    def _fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {"errors": {}}

    monkeypatch.setattr(pipeline, "run_pipeline", _fake_run_pipeline)

    result = runner.invoke(cli.app, ["run", "enrich", "--show-browser", "--dry-run"])

    assert result.exit_code == 0
    assert captured["headless"] is False
