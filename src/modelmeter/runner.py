"""Benchmark execution orchestrator.

Coordinates dataset loading, provider invocations, metric collection,
and summary aggregation across all configured models.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Callable

from modelmeter.config import BenchmarkConfig, Task
from modelmeter.providers import get_provider_adapter
from modelmeter.scoring import (
    CallResult,
    ProviderSummary,
    aggregate_provider_results,
    compute_weighted_scores,
)


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text).strip().casefold()


def evaluate_quality(actual: str, expected: str | None) -> float:
    """Deterministic quality evaluation for a single answer.

    - If no expected answer is set, return 1.0 (prompt succeeded).
    - If expected is set, return 1.0 when it appears in the answer after Unicode
      NFKC normalization and case folding, else 0.0.
    """
    if expected is None:
        return 1.0
    norm_actual = _normalize(actual)
    norm_expected = _normalize(expected)
    if norm_expected in norm_actual:
        return 1.0
    return 0.0


def calculate_cost(
    in_tokens: int,
    out_tokens: int,
    in_cost_per_1m: float,
    out_cost_per_1m: float,
) -> float:
    """Calculate USD cost for a token count based on per-1M-token pricing."""
    in_cost = (in_tokens / 1_000_000.0) * in_cost_per_1m
    out_cost = (out_tokens / 1_000_000.0) * out_cost_per_1m
    return in_cost + out_cost


def run_benchmark(
    config: BenchmarkConfig,
    tasks: list[Task],
    on_progress: Callable[[str, int, int], None] | None = None,
) -> list[ProviderSummary]:
    """Execute all tasks against all configured providers.

    Catches individual call failures gracefully so the benchmark continues.
    Returns ranked ProviderSummary list sorted by weighted score.
    """
    all_summaries: list[ProviderSummary] = []
    total_tasks = len(tasks) * config.repeats

    for p_cfg in config.providers:
        adapter = get_provider_adapter(p_cfg)
        p_results: list[CallResult] = []
        completed_count = 0

        for _ in range(config.repeats):
            for task in tasks:
                try:
                    resp = adapter.execute(task.prompt)
                    q = evaluate_quality(resp.text, task.expected)
                    cost = calculate_cost(
                        resp.input_tokens,
                        resp.output_tokens,
                        p_cfg.input_cost_per_1m,
                        p_cfg.output_cost_per_1m,
                    )
                    p_results.append(
                        CallResult(
                            task_id=task.id,
                            provider_name=p_cfg.name,
                            latency_ms=resp.latency_ms,
                            input_tokens=resp.input_tokens,
                            output_tokens=resp.output_tokens,
                            cost=cost,
                            quality=q,
                            success=True,
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - benchmark traps errors to report failure rate
                    p_results.append(
                        CallResult(
                            task_id=task.id,
                            provider_name=p_cfg.name,
                            latency_ms=0.0,
                            input_tokens=0,
                            output_tokens=0,
                            cost=0.0,
                            quality=0.0,
                            success=False,
                            error=str(exc),
                        )
                    )
                completed_count += 1
                if on_progress:
                    on_progress(p_cfg.name, completed_count, total_tasks)

        summary = aggregate_provider_results(p_cfg.name, p_results)
        all_summaries.append(summary)

    return compute_weighted_scores(all_summaries, config.weights)
