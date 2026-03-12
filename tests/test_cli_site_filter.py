from __future__ import annotations

from typer.testing import CliRunner

import applypilot.cli as cli
import applypilot.pipeline as pipeline


runner = CliRunner()


def test_run_passes_site_filter_to_pipeline(monkeypatch) -> None:
    monkeypatch.setattr(cli, "_bootstrap", lambda: None)
    captured: dict[str, object] = {}

    def _fake_run_pipeline(**kwargs):
        captured.update(kwargs)
        return {"errors": {}}

    monkeypatch.setattr(pipeline, "run_pipeline", _fake_run_pipeline)

    result = runner.invoke(
        cli.app,
        [
            "run",
            "discover",
            "--dry-run",
            "--site-filter",
            "Lensa",
            "--site-filter",
            "Dice",
        ],
    )

    assert result.exit_code == 0
    assert captured["site_filter"] == ["Lensa", "Dice"]
