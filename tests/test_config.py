"""Tests for config models: valid data, validation failures, weight rules."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from modelmeter.config import (
    BenchmarkConfig,
    ProviderConfig,
    Task,
    Weights,
    load_benchmark_config,
)

PROVIDER = {
    "name": "prov-a",
    "base_url": "https://api.example.com/v1",
    "model": "m-1",
    "api_key_env": "PROV_A_KEY",
}


def test_task_minimal() -> None:
    task = Task(id="t1", prompt="hello")
    assert task.expected is None


def test_task_rejects_empty_prompt() -> None:
    with pytest.raises(ValidationError):
        Task(id="t1", prompt="")


def test_provider_defaults() -> None:
    provider = ProviderConfig(**PROVIDER)
    assert provider.kind == "openai-compatible"
    assert provider.timeout_seconds == 30.0
    assert provider.input_cost_per_1m == 0.0


def test_provider_rejects_unknown_kind() -> None:
    with pytest.raises(ValidationError, match="unknown provider kind"):
        ProviderConfig(**PROVIDER, kind="mystery")


def test_weights_must_sum_to_one() -> None:
    with pytest.raises(ValidationError, match="sum to 1.0"):
        Weights(quality=0.5, latency=0.4, cost=0.0)


def test_weights_valid() -> None:
    weights = Weights(quality=0.6, latency=0.2, cost=0.2)
    assert weights.quality == pytest.approx(0.6)


def test_config_requires_provider() -> None:
    with pytest.raises(ValidationError):
        BenchmarkConfig(providers=[], dataset="tasks.jsonl")


def test_load_benchmark_config_roundtrip(tmp_path) -> None:
    config_file = tmp_path / "bench.json"
    config_file.write_text(
        """
        {
          "providers": [{"name": "prov-a", "base_url": "https://api.example.com/v1",
                         "model": "m-1", "api_key_env": "PROV_A_KEY"}],
          "dataset": "tasks.jsonl"
        }
        """,
        encoding="utf-8",
    )
    parsed = load_benchmark_config(config_file)
    assert len(parsed.providers) == 1
    assert str(parsed.dataset) == "tasks.jsonl"


def test_load_benchmark_config_missing_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_benchmark_config(tmp_path / "nope.json")


def test_config_rejects_duplicate_provider_names() -> None:
    other = {**PROVIDER, "model": "m-2"}
    with pytest.raises(ValidationError, match="duplicate provider names: prov-a"):
        BenchmarkConfig(providers=[PROVIDER, other], dataset="tasks.jsonl")


def test_config_allows_distinct_provider_names() -> None:
    other = {**PROVIDER, "name": "prov-b"}
    cfg = BenchmarkConfig(providers=[PROVIDER, other], dataset="tasks.jsonl")
    assert [p.name for p in cfg.providers] == ["prov-a", "prov-b"]
