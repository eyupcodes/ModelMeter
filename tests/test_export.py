"""Tests for exporting benchmark summaries to JSON and CSV."""

from __future__ import annotations

import csv
import json

from modelmeter.export import export_csv, export_json, export_markdown
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


def test_exports_include_first_error(tmp_path) -> None:
    summaries = [ProviderSummary(provider_name="p1", first_error="HTTP 401")]

    export_json(summaries, tmp_path / "out.json")
    export_csv(summaries, tmp_path / "out.csv")

    loaded = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert loaded[0]["first_error"] == "HTTP 401"
    with (tmp_path / "out.csv").open(encoding="utf-8") as f:
        assert list(csv.DictReader(f))[0]["first_error"] == "HTTP 401"


def test_export_markdown_table_in_given_order(tmp_path) -> None:
    summaries = [
        ProviderSummary(
            provider_name="best",
            weighted_score=91.26,
            avg_quality=1.0,
            failure_rate=0.25,
            p50_latency_ms=120.4,
            p95_latency_ms=300.6,
            cost_per_test=0.0012345,
            first_error="HTTP 500",
        ),
        ProviderSummary(provider_name="second", weighted_score=40.0),
    ]
    path = tmp_path / "out.md"

    export_markdown(summaries, path)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4
    assert lines[0].startswith("| Rank | Provider | Score |")
    assert lines[1].count("---") == 9
    assert (
        lines[2]
        == "| 1 | best | 91.3 | 1.00 | 25.0% | 120 | 301 | 0.001234 | HTTP 500 |"
    )
    assert lines[3].startswith("| 2 | second | 40.0 |")
    assert lines[3].endswith("|  |")


def test_export_markdown_escapes_cell_content(tmp_path) -> None:
    summaries = [
        ProviderSummary(
            provider_name="a|b <i>x</i>",
            first_error="line one\nline | two",
        )
    ]
    path = tmp_path / "out.md"

    export_markdown(summaries, path)

    row = path.read_text(encoding="utf-8").splitlines()[2]
    assert "a\\|b &lt;i&gt;x&lt;/i&gt;" in row
    assert "line one line \\| two" in row
    assert "\n" not in row
    # Escaped pipes aside, the row keeps exactly nine cells.
    assert row.replace("\\|", "").count("|") == 10


def test_export_markdown_empty_summaries_writes_header_only(tmp_path) -> None:
    path = tmp_path / "out.md"

    export_markdown([], path)

    assert len(path.read_text(encoding="utf-8").splitlines()) == 2
