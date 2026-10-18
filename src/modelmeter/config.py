"""Configuration models for benchmarks.

Pure data definitions — no IO, no CLI. Loaded/validated from JSON files by
the CLI layer; the core consumes validated instances only.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator


class Task(BaseModel):
    """A single benchmark task: prompt sent to every provider."""

    id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    expected: str | None = None


class ProviderConfig(BaseModel):
    """Connection + pricing definition for one provider/model pair."""

    name: str = Field(min_length=1)
    kind: str = Field(default="openai-compatible")
    base_url: str = Field(min_length=1)
    model: str = Field(min_length=1)
    api_key_env: str = Field(min_length=1)
    input_cost_per_1m: float = Field(default=0.0, ge=0)
    output_cost_per_1m: float = Field(default=0.0, ge=0)
    timeout_seconds: float = Field(default=30.0, gt=0)

    @field_validator("kind")
    @classmethod
    def _known_kind(cls, value: str) -> str:
        allowed = {"openai-compatible"}
        if value not in allowed:
            raise ValueError(
                f"unknown provider kind {value!r}; allowed: {sorted(allowed)}"
            )
        return value


class Weights(BaseModel):
    """Relative importance of each metric in the weighted score.

    Normalized so that quality + latency + cost == 1.0.
    """

    quality: float = Field(ge=0, le=1)
    latency: float = Field(ge=0, le=1)
    cost: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def _sums_to_one(self) -> Weights:
        total = self.quality + self.latency + self.cost
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"weights must sum to 1.0, got {total}")
        return self


class BenchmarkConfig(BaseModel):
    """Top-level benchmark definition."""

    providers: list[ProviderConfig] = Field(min_length=1)
    dataset: Path
    weights: Weights = Field(
        default_factory=lambda: Weights(quality=1.0, latency=0.0, cost=0.0)
    )
    repeats: int = Field(default=1, ge=1, le=10)

    @model_validator(mode="after")
    def _unique_provider_names(self) -> BenchmarkConfig:
        seen: set[str] = set()
        duplicates: list[str] = []
        for provider in self.providers:
            if provider.name in seen and provider.name not in duplicates:
                duplicates.append(provider.name)
            seen.add(provider.name)
        if duplicates:
            raise ValueError(f"duplicate provider names: {', '.join(duplicates)}")
        return self


def load_benchmark_config(path: Path) -> BenchmarkConfig:
    """Parse and validate a benchmark config JSON file."""
    import json

    raw = json.loads(path.read_text(encoding="utf-8"))
    return BenchmarkConfig.model_validate(raw)
