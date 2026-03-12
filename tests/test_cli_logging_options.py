from __future__ import annotations

import logging

from typer.testing import CliRunner

import applypilot.cli as cli


runner = CliRunner()


def test_parse_log_level_accepts_standard_levels() -> None:
    assert cli._parse_log_level("info") == logging.INFO
    assert cli._parse_log_level("WARNING") == logging.WARNING


def test_configure_logging_treats_http_as_debug_noise() -> None:
    cli._configure_logging(level="info")
    assert logging.getLogger("httpx").level == logging.WARNING

    cli._configure_logging(level="debug")
    assert logging.getLogger("httpx").level == logging.INFO


def test_configure_logging_clears_litellm_handlers() -> None:
    logger = logging.getLogger("LiteLLM")
    logger.handlers[:] = [logging.StreamHandler()]

    cli._configure_logging(level="debug")

    assert logger.handlers == []
    assert logger.propagate is True


def test_root_help_includes_logging_options() -> None:
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    assert "--log-level" in result.output
    assert "--log-file" in result.output
