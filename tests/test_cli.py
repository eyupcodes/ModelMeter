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


def test_run_missing_config() -> None:
    result = runner.invoke(app, ["run", "--config", "missing.json"])
    assert result.exit_code == 1


def test_run_missing_dataset(tmp_path) -> None:
    cfg = tmp_path / "bench.json"
    cfg.write_text(
        """
        {
          "providers": [{"name": "p1", "base_url": "http://x", "model": "m", "api_key_env": "K"}],
          "dataset": "missing_tasks.jsonl"
        }
        """,
        encoding="utf-8",
    )
    result = runner.invoke(app, ["run", "--config", str(cfg)])
    assert result.exit_code == 1
    assert "dataset file not found" in result.output.lower()


def test_run_end_to_end_with_exports(tmp_path, monkeypatch) -> None:
    import modelmeter.runner as runner_mod
    from modelmeter.providers import BaseProvider, ProviderResponse

    class FakeProvider(BaseProvider):
        def execute(self, prompt: str) -> ProviderResponse:
            return ProviderResponse(
                text="4",
                input_tokens=10,
                output_tokens=5,
                latency_ms=80.0,
            )

    monkeypatch.setattr(
        runner_mod, "get_provider_adapter", lambda cfg: FakeProvider(cfg)
    )

    tasks_file = tmp_path / "tasks.jsonl"
    tasks_file.write_text(
        '{"id": "t1", "prompt": "2+2?", "expected": "4"}\n', encoding="utf-8"
    )

    cfg_file = tmp_path / "bench.json"
    cfg_file.write_text(
        f"""
        {{
          "providers": [{{"name": "mock-p1", "base_url": "http://x", "model": "m", "api_key_env": "K"}}],
          "dataset": "{tasks_file.name}"
        }}
        """,
        encoding="utf-8",
    )

    out_json = tmp_path / "results.json"
    out_csv = tmp_path / "results.csv"

    result = runner.invoke(
        app,
        [
            "run",
            "--config",
            str(cfg_file),
            "--json",
            str(out_json),
            "--csv",
            str(out_csv),
        ],
    )
    assert result.exit_code == 0
    assert "Leaderboard" in result.output
    assert "mock-p1" in result.output
    assert out_json.is_file()
    assert out_csv.is_file()


def test_check_rejects_duplicate_provider_names(tmp_path) -> None:
    provider = (
        '{"name": "p1", "base_url": "http://x", "model": "m", "api_key_env": "K"}'
    )
    cfg = tmp_path / "dup.json"
    cfg.write_text(
        f'{{"providers": [{provider}, {provider}], "dataset": "tasks.jsonl"}}',
        encoding="utf-8",
    )
    result = runner.invoke(app, ["check", "--config", str(cfg)])
    assert result.exit_code == 1
    assert "duplicate provider names" in result.output


def test_run_shows_why_calls_failed(tmp_path, monkeypatch) -> None:
    import modelmeter.runner as runner_mod
    from modelmeter.providers import BaseProvider, ProviderResponse

    class FailingProvider(BaseProvider):
        def execute(self, prompt: str) -> ProviderResponse:
            raise ValueError("Missing environment variable 'K' [for p1]")

    monkeypatch.setattr(
        runner_mod, "get_provider_adapter", lambda cfg: FailingProvider(cfg)
    )
    (tmp_path / "tasks.jsonl").write_text(
        '{"id": "t1", "prompt": "2+2?"}\n', encoding="utf-8"
    )
    cfg_file = tmp_path / "bench.json"
    cfg_file.write_text(
        '{"providers": [{"name": "p1", "base_url": "http://x", "model": "m", '
        '"api_key_env": "K"}], "dataset": "tasks.jsonl"}',
        encoding="utf-8",
    )

    result = runner.invoke(app, ["run", "--config", str(cfg_file)])

    assert result.exit_code == 0
    assert "1/1 calls failed" in result.output
    assert "Missing environment variable 'K' [for p1]" in result.output


def _write_config(tmp_path, dataset="tasks.jsonl"):
    cfg = tmp_path / "bench.json"
    cfg.write_text(
        '{"providers": [{"name": "p1", "base_url": "http://x", "model": "m",'
        f' "api_key_env": "K"}}], "dataset": "{dataset}"}}',
        encoding="utf-8",
    )
    return cfg


def test_run_empty_dataset(tmp_path) -> None:
    (tmp_path / "tasks.jsonl").write_text("", encoding="utf-8")
    result = runner.invoke(app, ["run", "--config", str(_write_config(tmp_path))])
    assert result.exit_code == 1
    assert "dataset is empty" in result.output.lower()


def test_run_unreadable_dataset(tmp_path) -> None:
    (tmp_path / "tasks.jsonl").write_text("not json\n", encoding="utf-8")
    result = runner.invoke(app, ["run", "--config", str(_write_config(tmp_path))])
    assert result.exit_code == 1
    assert "failed loading dataset" in result.output.lower()


def test_run_invalid_config(tmp_path) -> None:
    cfg = tmp_path / "bench.json"
    cfg.write_text('{"dataset": "tasks.jsonl"}', encoding="utf-8")
    result = runner.invoke(app, ["run", "--config", str(cfg)])
    assert result.exit_code == 1
    assert "invalid config" in result.output.lower()


def test_run_bad_export_path_fails_before_calling_providers(
    tmp_path, monkeypatch
) -> None:
    import modelmeter.runner as runner_mod

    def boom(cfg):
        raise AssertionError("provider must not be called")

    monkeypatch.setattr(runner_mod, "get_provider_adapter", boom)
    (tmp_path / "tasks.jsonl").write_text('{"id": "t1", "prompt": "p"}\n')
    cfg = str(_write_config(tmp_path))

    missing_dir = tmp_path / "nope" / "out.json"
    result = runner.invoke(app, ["run", "--config", cfg, "--json", str(missing_dir)])
    assert result.exit_code == 1
    assert "directory does not exist" in result.output

    result = runner.invoke(app, ["run", "--config", cfg, "--csv", str(tmp_path)])
    assert result.exit_code == 1
    assert "is a directory" in result.output


def test_run_export_write_error_is_reported(tmp_path, monkeypatch) -> None:
    import modelmeter.cli as cli_mod

    monkeypatch.setattr(cli_mod, "run_benchmark", lambda cfg, tasks: [])

    def deny(summaries, path):
        raise PermissionError("denied")

    monkeypatch.setattr(cli_mod, "export_json", deny)
    (tmp_path / "tasks.jsonl").write_text('{"id": "t1", "prompt": "p"}\n')
    out = tmp_path / "out.json"
    result = runner.invoke(
        app,
        ["run", "--config", str(_write_config(tmp_path)), "--json", str(out)],
    )
    assert result.exit_code == 1
    assert "cannot write export" in result.output
