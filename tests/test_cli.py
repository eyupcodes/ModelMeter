"""CLI smoke tests: --help and check subcommands."""

from __future__ import annotations

from typer.testing import CliRunner

from modelmeter.cli import app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "modelmeter" in result.output.lower()


def test_cli_version() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "modelmeter" in result.output.lower()


def test_check_missing_file() -> None:
    result = runner.invoke(app, ["check", "--config", "nonexistent.json"])
    assert result.exit_code == 1


def test_check_invalid_config(tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"dataset": "tasks.jsonl"}', encoding="utf-8")
    result = runner.invoke(app, ["check", "--config", str(bad)])
    assert result.exit_code == 1
