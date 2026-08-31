# ModelMeter

Compare LLMs on quality, latency, token usage and cost — over the same test set, from one CLI command.

Model selection is usually based on brand or subjective feel. ModelMeter replaces that with numbers: run every provider against the same task dataset and get a weighted leaderboard.

## Install

Requires Python 3.11+.

```bash
git clone <repository-url>
cd modelmeter
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -e ".[dev]"
```

## Usage

```bash
modelmeter --help
modelmeter check --config examples/benchmark.example.json
```

## Status

Work in progress — see [4A/AGENT_ROADMAP.md](4A/AGENT_ROADMAP.md) for the milestone plan.

## License

MIT — see [LICENSE](LICENSE).
