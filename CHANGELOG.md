# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- CI now runs `ruff format --check` and `ruff check`; existing findings were fixed (#3).

## [0.1.0] - 2026-08-31

### Added
- Benchmark configuration model with Pydantic validation (providers, datasets, weights, repeats).
- OpenAI-compatible provider adapter supporting any standard `/v1/chat/completions` endpoint (OpenAI, Groq, Mistral, vLLM, etc.).
- JSONL task dataset loader with line-numbered validation errors.
- Benchmark runner tracking latency (p50/p95), input/output tokens, per-test cost, failure rate, and deterministic quality scoring.
- Weighted multi-metric scoring algorithm normalizing quality, latency, and cost into a 0-100 scale penalized by failures.
- Rich CLI leaderboard with sorted rankings and color-coded metrics.
- JSON and CSV benchmark results export.
- Config validation command (`modelmeter check --config <file>`).
- Ready-to-use example config and dataset under `examples/`.
- 39 automated tests with 95% code coverage.
- GitHub Actions CI workflow for automated testing on Python 3.11.
