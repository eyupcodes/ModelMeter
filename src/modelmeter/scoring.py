"""Metrics aggregation and weighted scoring logic.

Pure computation — no IO, no network calls.
"""

from __future__ import annotations

import math

from pydantic import BaseModel

from modelmeter.config import Weights


class CallResult(BaseModel):
    """Raw result of a single provider attempt on a single task."""

    task_id: str
    provider_name: str
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    quality: float = 0.0  # 0.0 to 1.0 (exact/normalized match with expected, or 1.0 if ok and no expected)
    success: bool = True
    error: str | None = None


class ProviderSummary(BaseModel):
    """Aggregated benchmark statistics for one provider."""

    provider_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failure_rate: float = 0.0
    avg_quality: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    cost_per_test: float = 0.0
    weighted_score: float = 0.0  # 0.0 to 100.0


def percentile(values: list[float], p: float) -> float:
    """Calculate the p-th percentile (0 <= p <= 100) of a list of values."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    k = (len(sorted_v) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(sorted_v[int(k)])
    d0 = sorted_v[int(f)] * (c - k)
    d1 = sorted_v[int(c)] * (k - f)
    return float(d0 + d1)


def aggregate_provider_results(
    provider_name: str,
    results: list[CallResult],
) -> ProviderSummary:
    """Aggregate a list of CallResults for a single provider."""
    total = len(results)
    if total == 0:
        return ProviderSummary(provider_name=provider_name)

    successes = [r for r in results if r.success]
    failures = [r for r in results if not r.success]

    successful_calls = len(successes)
    failure_rate = len(failures) / total

    avg_quality = sum(r.quality for r in results) / total if total > 0 else 0.0

    latencies = [r.latency_ms for r in successes]
    p50_lat = percentile(latencies, 50)
    p95_lat = percentile(latencies, 95)

    tot_in_tokens = sum(r.input_tokens for r in results)
    tot_out_tokens = sum(r.output_tokens for r in results)
    tot_cost = sum(r.cost for r in results)
    cost_per_test = tot_cost / total if total > 0 else 0.0

    return ProviderSummary(
        provider_name=provider_name,
        total_calls=total,
        successful_calls=successful_calls,
        failure_rate=round(failure_rate, 4),
        avg_quality=round(avg_quality, 4),
        p50_latency_ms=round(p50_lat, 2),
        p95_latency_ms=round(p95_lat, 2),
        total_input_tokens=tot_in_tokens,
        total_output_tokens=tot_out_tokens,
        total_tokens=tot_in_tokens + tot_out_tokens,
        total_cost=round(tot_cost, 6),
        cost_per_test=round(cost_per_test, 6),
        weighted_score=0.0,
    )


def compute_weighted_scores(
    summaries: list[ProviderSummary],
    weights: Weights,
) -> list[ProviderSummary]:
    """Calculate normalized weighted scores (0-100) across providers.

    Higher quality -> better (direct)
    Lower latency -> better (inverse relative to max)
    Lower cost -> better (inverse relative to max)
    """
    if not summaries:
        return []

    max_p50 = max((s.p50_latency_ms for s in summaries), default=0.0)
    max_cost = max((s.cost_per_test for s in summaries), default=0.0)

    updated: list[ProviderSummary] = []
    for s in summaries:
        q_score = s.avg_quality  # 0..1

        if max_p50 > 0:
            l_score = max(0.0, 1.0 - (s.p50_latency_ms / max_p50))
        else:
            l_score = 1.0

        if max_cost > 0:
            c_score = max(0.0, 1.0 - (s.cost_per_test / max_cost))
        else:
            c_score = 1.0

        raw_score = (
            (weights.quality * q_score)
            + (weights.latency * l_score)
            + (weights.cost * c_score)
        ) * 100.0

        final_score = raw_score * (1.0 - s.failure_rate)

        summary_dict = s.model_dump()
        summary_dict["weighted_score"] = round(final_score, 2)
        updated.append(ProviderSummary(**summary_dict))

    return sorted(updated, key=lambda x: x.weighted_score, reverse=True)
