"""Tests for metrics calculation and weighted scoring logic."""

from __future__ import annotations

import pytest

from modelmeter.config import Weights
from modelmeter.scoring import (
    CallResult,
    ProviderSummary,
    aggregate_provider_results,
    compute_weighted_scores,
    percentile,
)


def test_percentile_empty() -> None:
    assert percentile([], 50) == 0.0


def test_percentile_exact() -> None:
    vals = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert percentile(vals, 50) == 30.0
    assert percentile(vals, 0) == 10.0
    assert percentile(vals, 100) == 50.0


def test_aggregate_empty() -> None:
    summary = aggregate_provider_results("test", [])
    assert summary.provider_name == "test"
    assert summary.total_calls == 0
    assert summary.failure_rate == 0.0


def test_aggregate_mixed_results() -> None:
    results = [
        CallResult(
            task_id="1",
            provider_name="p1",
            latency_ms=100.0,
            input_tokens=10,
            output_tokens=20,
            cost=0.001,
            quality=1.0,
            success=True,
        ),
        CallResult(
            task_id="2",
            provider_name="p1",
            latency_ms=200.0,
            input_tokens=10,
            output_tokens=20,
            cost=0.001,
            quality=0.5,
            success=True,
        ),
        CallResult(
            task_id="3",
            provider_name="p1",
            latency_ms=0.0,
            input_tokens=0,
            output_tokens=0,
            cost=0.0,
            quality=0.0,
            success=False,
            error="timeout",
        ),
    ]
    summary = aggregate_provider_results("p1", results)
    assert summary.total_calls == 3
    assert summary.successful_calls == 2
    assert summary.failure_rate == pytest.approx(0.3333, abs=1e-3)
    assert summary.avg_quality == pytest.approx(0.5, abs=1e-3)
    assert summary.total_tokens == 60
    assert summary.cost_per_test == pytest.approx(0.002 / 3, abs=1e-5)


def test_compute_weighted_scores_sorting() -> None:
    weights = Weights(quality=0.6, latency=0.2, cost=0.2)
    s1 = ProviderSummary(
        provider_name="fast_cheap_good",
        total_calls=1,
        successful_calls=1,
        avg_quality=1.0,
        p50_latency_ms=50.0,
        cost_per_test=0.001,
        failure_rate=0.0,
    )
    s2 = ProviderSummary(
        provider_name="slow_expensive_bad",
        total_calls=1,
        successful_calls=1,
        avg_quality=0.2,
        p50_latency_ms=500.0,
        cost_per_test=0.010,
        failure_rate=0.0,
    )
    ranked = compute_weighted_scores([s2, s1], weights)
    assert len(ranked) == 2
    assert ranked[0].provider_name == "fast_cheap_good"
    assert ranked[0].weighted_score > ranked[1].weighted_score


def test_aggregate_keeps_first_error_message() -> None:
    results = [
        CallResult(task_id="t1", provider_name="p", quality=1.0),
        CallResult(task_id="t2", provider_name="p", success=False, error="HTTP 401"),
        CallResult(task_id="t3", provider_name="p", success=False, error="timeout"),
    ]

    summary = aggregate_provider_results("p", results)

    assert summary.first_error == "HTTP 401"


def test_aggregate_without_failures_has_no_error() -> None:
    summary = aggregate_provider_results(
        "p", [CallResult(task_id="t1", provider_name="p", quality=1.0)]
    )

    assert summary.first_error is None


def test_weighted_scores_preserve_first_error() -> None:
    summary = aggregate_provider_results(
        "p", [CallResult(task_id="t1", provider_name="p", success=False, error="boom")]
    )

    ranked = compute_weighted_scores(
        [summary], Weights(quality=0.5, latency=0.3, cost=0.2)
    )

    assert ranked[0].first_error == "boom"
