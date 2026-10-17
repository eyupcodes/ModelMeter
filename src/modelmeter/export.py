"""Export benchmark summaries to JSON and CSV files."""

from __future__ import annotations

import csv
import json
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
