# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- A blank `expected` in a task dataset is rejected with a line-numbered error instead of scoring every reply as correct (#27).
- Expected answers are matched after Unicode NFKC normalization and case folding, so composed and decomposed accents (and `ß`/`SS`) no longer count as wrong (#27).
- Task datasets and benchmark configs with a UTF-8 BOM (Excel, Windows editors) now load instead of failing as invalid JSON (#25).
- A `null`, negative or non-integer token count in a provider's `usage` is read as 0 instead of failing an otherwise successful call (#23).

### Added
- Regression coverage verifies repeated benchmarks keep accurate progress, failure diagnostics, token costs, and rankings when a provider fails between successful calls.
- Regression tests now verify exact leaderboard scores for individual and combined metric weights, partial and complete failures, and interpolated p50/p95 latencies.
- OpenAI-compatible providers retry HTTP 429 once, respecting `Retry-After` seconds or HTTP dates up to 30 seconds; retry time is included in measured latency.
- `api_key_env` is optional in provider configs, so keyless OpenAI-compatible endpoints such as a local Ollama or vLLM server can be benchmarked; no `Authorization` header is sent without it (#16).
- Providers with failed calls now show the first error message under the leaderboard, and `ProviderSummary` and the JSON/CSV exports gain a `first_error` field (#10).

### Fixed
- Task datasets are split on `\n` only, so a prompt containing U+2028, U+0085 or similar characters loads instead of failing with `invalid JSON`, and error line numbers match the file (#21).
- Provider replies without a completion (no `choices`, error payloads with HTTP 200, non-object bodies) are now recorded as failed calls with the provider's message, instead of successful calls with quality 1.0; `"usage": null` is treated as missing (#14).
- `modelmeter run` checks `--json`/`--csv` paths before calling any provider and reports an unwritable export path as a one-line error with exit code 1, instead of a traceback after the benchmark has finished (#12).
- Benchmark configs with duplicate provider names and datasets with duplicate task ids are now rejected with a clear error instead of producing ambiguous results (#8).

## [0.1.1] - 2026-10-17

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
