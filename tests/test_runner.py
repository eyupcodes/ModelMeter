"""Tests for the benchmark runner and helper functions."""

from __future__ import annotations

import pytest

from modelmeter.config import BenchmarkConfig, ProviderConfig, Task, Weights
from modelmeter.providers import BaseProvider, ProviderResponse
from modelmeter.runner import calculate_cost, evaluate_quality, run_benchmark


def test_evaluate_quality() -> None:
    # No expected -> 1.0
    assert evaluate_quality("anything", None) == 1.0
    # Expected match (case insensitive substring)
    assert evaluate_quality("The answer is 4.", "4") == 1.0
    assert evaluate_quality("PARIS", "paris") == 1.0
    # Mismatch -> 0.0
    assert evaluate_quality("Madrid", "Paris") == 0.0


def test_calculate_cost() -> None:
    # 1,000,000 in at $1.0 and 1,000,000 out at $2.0 = $3.0
    cost = calculate_cost(
        in_tokens=1_000_000,
        out_tokens=1_000_000,
        in_cost_per_1m=1.0,
        out_cost_per_1m=2.0,
    )
    assert cost == pytest.approx(3.0)


class FakeProvider(BaseProvider):
    def __init__(self, config: ProviderConfig, succeed: bool = True) -> None:
        super().__init__(config)
        self.succeed = succeed

    def execute(self, prompt: str) -> ProviderResponse:
        if not self.succeed:
            raise ConnectionError("Simulated network outage")
        return ProviderResponse(
            text="4",
            input_tokens=10,
            output_tokens=5,
            latency_ms=120.0,
        )


def test_run_benchmark_handles_provider_failure(monkeypatch) -> None:
    import modelmeter.runner as runner_mod

    p_cfg_good = ProviderConfig(
        name="good",
        base_url="https://api.example.com",
        model="m1",
        api_key_env="K1",
    )
    p_cfg_bad = ProviderConfig(
        name="bad",
        base_url="https://api.example.com",
        model="m2",
        api_key_env="K2",
    )

    def mock_get_adapter(cfg):
        if cfg.name == "good":
            return FakeProvider(cfg, succeed=True)
        return FakeProvider(cfg, succeed=False)

    monkeypatch.setattr(runner_mod, "get_provider_adapter", mock_get_adapter)

    bench_cfg = BenchmarkConfig(
        providers=[p_cfg_good, p_cfg_bad],
        dataset="fake.jsonl",
        weights=Weights(quality=1.0, latency=0.0, cost=0.0),
        repeats=1,
    )
    tasks = [Task(id="t1", prompt="2+2?", expected="4")]

    results = run_benchmark(bench_cfg, tasks)
    assert len(results) == 2
    good_res = next(r for r in results if r.provider_name == "good")
    bad_res = next(r for r in results if r.provider_name == "bad")

    assert good_res.successful_calls == 1
    assert good_res.failure_rate == 0.0
    assert good_res.weighted_score > 0

    assert bad_res.successful_calls == 0
    assert bad_res.failure_rate == 1.0
    assert bad_res.weighted_score == 0.0
