"""Hardening and edge-case tests across all components."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from modelmeter.cli import app
from modelmeter.config import Weights
from modelmeter.export import export_csv, export_json
from modelmeter.providers import get_provider_adapter
from modelmeter.scoring import (
    ProviderSummary,
    compute_weighted_scores,
    percentile,
)

runner = CliRunner()


def test_percentile_single_value() -> None:
    assert percentile([42.0], 50) == 42.0
    assert percentile([42.0], 95) == 42.0


def test_scoring_with_zero_max_latency_and_cost() -> None:
    # All providers have 0ms latency and 0 cost
    s1 = ProviderSummary(
        provider_name="p1",
        total_calls=1,
        successful_calls=1,
        avg_quality=1.0,
        p50_latency_ms=0.0,
        cost_per_test=0.0,
        failure_rate=0.0,
    )
    s2 = ProviderSummary(
        provider_name="p2",
        total_calls=1,
        successful_calls=1,
        avg_quality=0.5,
        p50_latency_ms=0.0,
        cost_per_test=0.0,
        failure_rate=0.0,
    )
    weights = Weights(quality=0.5, latency=0.3, cost=0.2)
    ranked = compute_weighted_scores([s1, s2], weights)
    assert len(ranked) == 2
    assert ranked[0].weighted_score > ranked[1].weighted_score


def test_export_empty_csv_and_json(tmp_path) -> None:
    csv_file = tmp_path / "empty.csv"
    json_file = tmp_path / "empty.json"
    export_csv([], csv_file)
    export_json([], json_file)
    assert csv_file.read_text(encoding="utf-8") == ""
    assert json_file.read_text(encoding="utf-8") == "[]"


def test_unknown_provider_kind_raises_factory() -> None:
    class DummyConfig:
        kind = "unsupported-provider"

    with pytest.raises(ValueError, match="Unsupported provider kind"):
        get_provider_adapter(DummyConfig())  # type: ignore


def test_cli_run_empty_dataset_error(tmp_path) -> None:
    tasks = tmp_path / "empty.jsonl"
    tasks.write_text("", encoding="utf-8")
    cfg = tmp_path / "bench.json"
    cfg.write_text(
        f"""
        {{
          "providers": [{{"name": "p1", "base_url": "http://x", "model": "m", "api_key_env": "K"}}],
          "dataset": "{tasks.name}"
        }}
        """,
        encoding="utf-8",
    )
    result = runner.invoke(app, ["run", "--config", str(cfg)])
    assert result.exit_code == 1
    assert "dataset is empty" in result.output.lower()
