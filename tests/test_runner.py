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


def test_run_benchmark_repeats_and_reports_progress_after_failures(monkeypatch) -> None:
    import modelmeter.runner as runner_mod

    responses = {
        "mixed": [
            ProviderResponse(
                text="4", input_tokens=10, output_tokens=5, latency_ms=100
            ),
            ConnectionError("first outage"),
            ProviderResponse(
                text="wrong", input_tokens=20, output_tokens=10, latency_ms=300
            ),
            TimeoutError("later timeout"),
        ],
        "healthy": [
            ProviderResponse(text="4", input_tokens=1, output_tokens=1, latency_ms=50)
        ]
        * 4,
    }
    prompts = {name: [] for name in responses}

    class ScriptedProvider(BaseProvider):
        def __init__(self, config: ProviderConfig) -> None:
            super().__init__(config)
            self.name = config.name
            self.responses = iter(responses[self.name])

        def execute(self, prompt: str) -> ProviderResponse:
            prompts[self.name].append(prompt)
            response = next(self.responses)
            if isinstance(response, Exception):
                raise response
            return response

    monkeypatch.setattr(runner_mod, "get_provider_adapter", ScriptedProvider)
    config = BenchmarkConfig(
        providers=[
            ProviderConfig(
                name=name,
                base_url="https://api.example.com",
                model="m",
                input_cost_per_1m=1.0,
                output_cost_per_1m=2.0,
            )
            for name in responses
        ],
        dataset="unused.jsonl",
        repeats=2,
        weights=Weights(quality=1.0, latency=0.0, cost=0.0),
    )
    tasks = [
        Task(id="t1", prompt="2+2?", expected="4"),
        Task(id="t2", prompt="2*2?", expected="4"),
    ]
    progress = []

    results = run_benchmark(
        config, tasks, on_progress=lambda *event: progress.append(event)
    )

    assert prompts == {name: ["2+2?", "2*2?", "2+2?", "2*2?"] for name in responses}
    assert progress == [
        (name, completed, 4)
        for name in ("mixed", "healthy")
        for completed in range(1, 5)
    ]
    assert [result.provider_name for result in results] == ["healthy", "mixed"]
    healthy, mixed = results
    assert mixed.total_calls == 4
    assert mixed.successful_calls == 2
    assert mixed.failure_rate == 0.5
    assert mixed.first_error == "first outage"
    assert mixed.avg_quality == 0.25
    assert mixed.p50_latency_ms == 200.0
    assert mixed.p95_latency_ms == 290.0
    assert mixed.total_input_tokens == 30
    assert mixed.total_output_tokens == 15
    assert mixed.total_tokens == 45
    assert mixed.total_cost == pytest.approx(0.00006)
    assert mixed.cost_per_test == pytest.approx(0.000015)
    assert mixed.weighted_score == 12.5
    assert healthy.total_calls == healthy.successful_calls == 4
    assert healthy.failure_rate == 0.0
    assert healthy.first_error is None
    assert healthy.total_tokens == 8
    assert healthy.total_cost == pytest.approx(0.000012)
    assert healthy.cost_per_test == pytest.approx(0.000003)
    assert healthy.weighted_score == 100.0
