# ModelMeter

Compare LLMs on **quality**, **latency**, **token usage**, and **cost** over the exact same test dataset — from a single CLI command.

```
🏆 ModelMeter Benchmark Leaderboard
┏━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Rank ┃ Provider            ┃  Score ┃ Avg Quality ┃ p50 Latency ┃ p95 Latency ┃ Total Tokens ┃ Cost / Test ┃ Failure Rate ┃
┡━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━┩
│  1   │ groq-llama-3.3-70b  │  88.45 │      100.0% │     180.2ms │     240.5ms │          420 │    $0.00012 │         0.0% │
│  2   │ openai-gpt4o-mini   │  85.20 │      100.0% │     420.0ms │     510.0ms │          390 │    $0.00008 │         0.0% │
│  3   │ mistral-small       │  76.10 │       80.0% │     350.0ms │     490.0ms │          410 │    $0.00011 │         0.0% │
└──────┴─────────────────────┴────────┴─────────────┴─────────────┴─────────────┴──────────────┴─────────────┴──────────────┘
```

---

## 1. Why ModelMeter?

Model selection in most teams relies on brand reputation or subjective vibes. ModelMeter replaces guesswork with reproducible numbers:

- **Same prompts, same time:** Evaluates every model against the identical task suite.
- **Multi-metric score:** Balances quality, speed, and API pricing using customizable weights.
- **Provider abstraction:** Uses a single standard OpenAI-compatible protocol to test OpenAI, Groq, Mistral, Together, vLLM, or any self-hosted endpoint.
- **Zero vendor lock-in:** Local-first CLI, no cloud account, no SaaS subscription, no telemetry.

---

## 2. Quick Start (30 seconds)

### Installation

Requires **Python 3.11+**.

```bash
git clone https://github.com/eyupcodes/ModelMeter.git
cd ModelMeter
python -m venv .venv
source .venv/bin/activate    # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Validate Configuration

```bash
modelmeter check --config examples/benchmark.example.json
```

### Run Benchmark

Set your API keys via environment variables (ModelMeter never stores secrets in files):

```bash
export OPENAI_API_KEY="sk-..."
export GROQ_API_KEY="gsk_..."
export MISTRAL_API_KEY="..."

modelmeter run --config examples/benchmark.example.json --json results.json --csv results.csv
```

---

## 3. Configuration

A benchmark config is a standard JSON file (`benchmark.json`):

```json
{
  "providers": [
    {
      "name": "openai-gpt4o-mini",
      "kind": "openai-compatible",
      "base_url": "https://api.openai.com/v1",
      "model": "gpt-4o-mini",
      "api_key_env": "OPENAI_API_KEY",
      "input_cost_per_1m": 0.15,
      "output_cost_per_1m": 0.60,
      "timeout_seconds": 30.0
    },
    {
      "name": "groq-llama-3.3-70b",
      "kind": "openai-compatible",
      "base_url": "https://api.groq.com/openai/v1",
      "model": "llama-3.3-70b-versatile",
      "api_key_env": "GROQ_API_KEY",
      "input_cost_per_1m": 0.59,
      "output_cost_per_1m": 0.79,
      "timeout_seconds": 30.0
    }
  ],
  "dataset": "tasks.jsonl",
  "weights": {
    "quality": 0.5,
    "latency": 0.3,
    "cost": 0.2
  },
  "repeats": 3
}
```

### Task Dataset (`tasks.jsonl`)

Each line is a JSON object with a prompt and an optional `expected` answer:

```jsonl
{"id": "math-1", "prompt": "What is 17 multiplied by 6? Answer with just the number.", "expected": "102"}
{"id": "geo-1", "prompt": "What is the capital of Japan?", "expected": "Tokyo"}
{"id": "code-1", "prompt": "Write a Python lambda that doubles x.", "expected": "lambda x: x * 2"}
```

---

## 4. Scoring Algorithm

Weighted scores are normalized between **0 and 100**:

$$\text{Score} = \left( w_q \cdot \text{Quality} + w_l \cdot \text{SpeedScore} + w_c \cdot \text{CostScore} \right) \times 100 \times (1 - \text{FailureRate})$$

- $\text{Quality}$: Ratio of answers matching the expected target (1.0 if no target specified).
- $\text{SpeedScore}$: Relative $p50$ latency ($1 - \frac{p50}{\max(p50)}$).
- $\text{CostScore}$: Relative cost per test ($1 - \frac{\text{cost}}{\max(\text{cost})}$).
- $\text{FailureRate}$: Penalizes timeouts and API errors directly.

---

## 5. CLI Commands

| Command | Description |
|---|---|
| `modelmeter --help` | Show available options and commands |
| `modelmeter version` | Print installed version |
| `modelmeter check --config <file>` | Validate benchmark configuration and dataset path |
| `modelmeter run --config <file>` | Run benchmark and render Rich leaderboard table |
| `modelmeter run --config <file> --json <out.json>` | Export full results to JSON |
| `modelmeter run --config <file> --csv <out.csv>` | Export summary table to CSV |

---

## 6. Architecture & Principles

- **Separation of Concerns:** Pure computation (metrics, scoring, config validation) has zero IO and zero external dependencies.
- **Resilience:** Individual provider failures (timeouts, network glitches) are captured and reflected in the failure rate without stopping the benchmark.
- **Security:** API keys are read strictly from environment variables at execution time. No credentials are saved in config files, logs, or exports.

---

## 7. Testing

```bash
# Run unit, integration and hardening tests with coverage
pytest --cov=modelmeter --cov-report=term-missing
```

Currently **39 tests** covering **95%** of the codebase.

---

## 8. License

[MIT](LICENSE) © 2026 ModelMeter contributors.
