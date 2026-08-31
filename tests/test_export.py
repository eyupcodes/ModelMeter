"""Tests for exporting benchmark summaries to JSON and CSV."""

from __future__ import annotations

import csv
import json

from modelmeter.export import export_csv, export_json
from modelmeter.scoring import ProviderSummary


def test_export_json_and_csv(tmp_path) -> None:
    summaries = [
        ProviderSummary(
            provider_name="p1",
            total_calls=2,
            successful_calls=2,
            avg_quality=1.0,
            p50_latency_ms=100.0,
            p95_latency_ms=150.0,
            total_tokens=100,
            cost_per_test=0.001,
            failure_rate=0.0,
            weighted_score=95.5,
        )
    ]

    json_path = tmp_path / "out.json"
    export_json(summaries, json_path)
    loaded_json = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(loaded_json) == 1
    assert loaded_json[0]["provider_name"] == "p1"
    assert loaded_json[0]["weighted_score"] == 95.5

    csv_path = tmp_path / "out.csv"
    export_csv(summaries, csv_path)
    with csv_path.open(encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 1
    assert reader[0]["provider_name"] == "p1"
    assert float(reader[0]["weighted_score"]) == 95.5
