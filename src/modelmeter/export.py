"""Export benchmark summaries to JSON, CSV and Markdown files."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from modelmeter.scoring import ProviderSummary


def export_json(summaries: list[ProviderSummary], path: Path) -> None:
    """Save summaries to a JSON file."""
    data = [s.model_dump() for s in summaries]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def export_csv(summaries: list[ProviderSummary], path: Path) -> None:
    """Save summaries to a CSV file."""
    if not summaries:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(summaries[0].model_dump().keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for s in summaries:
            writer.writerow(s.model_dump())


_MARKDOWN_HEADERS = (
    "Rank",
    "Provider",
    "Score",
    "Quality",
    "Failure rate",
    "p50 ms",
    "p95 ms",
    "Cost / test (USD)",
    "First error",
)


def _escape_cell(text: str) -> str:
    """Make arbitrary text safe inside one GitHub-flavoured Markdown table cell."""
    collapsed = re.sub(r"\s+", " ", text).strip()
    escaped = (
        collapsed.replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("`", "\\`")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return escaped


def export_markdown(summaries: list[ProviderSummary], path: Path) -> None:
    """Save the leaderboard as a Markdown table, in the order given (best first)."""
    lines = [
        "| " + " | ".join(_MARKDOWN_HEADERS) + " |",
        "|" + "|".join([" --- "] * len(_MARKDOWN_HEADERS)) + "|",
    ]
    for rank, s in enumerate(summaries, start=1):
        cells = (
            str(rank),
            _escape_cell(s.provider_name),
            f"{s.weighted_score:.1f}",
            f"{s.avg_quality:.2f}",
            f"{s.failure_rate * 100:.1f}%",
            f"{s.p50_latency_ms:.0f}",
            f"{s.p95_latency_ms:.0f}",
            f"{s.cost_per_test:.6f}",
            _escape_cell(s.first_error) if s.first_error else "",
        )
        lines.append("| " + " | ".join(cells) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
