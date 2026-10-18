"""Tests for JSONL dataset loading: valid input, malformed lines, edge cases."""

from __future__ import annotations

import pytest

from modelmeter.dataset import load_tasks


def write_jsonl(tmp_path, lines):
    path = tmp_path / "tasks.jsonl"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_load_valid_tasks(tmp_path) -> None:
    path = write_jsonl(
        tmp_path,
        [
            '{"id": "t1", "prompt": "What is 2+2?", "expected": "4"}',
            '{"id": "t2", "prompt": "Capital of France?"}',
        ],
    )
    tasks = load_tasks(path)
    assert len(tasks) == 2
    assert tasks[0].id == "t1"
    assert tasks[1].expected is None


def test_skips_blank_lines(tmp_path) -> None:
    path = write_jsonl(
        tmp_path,
        ["", '{"id": "t1", "prompt": "hi"}', "  ", ""],
    )
    tasks = load_tasks(path)
    assert len(tasks) == 1


def test_empty_file_gives_empty_list(tmp_path) -> None:
    path = tmp_path / "tasks.jsonl"
    path.write_text("", encoding="utf-8")
    assert load_tasks(path) == []


def test_missing_file_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_tasks(tmp_path / "nope.jsonl")


def test_invalid_json_reports_line_number(tmp_path) -> None:
    path = write_jsonl(
        tmp_path,
        ['{"id": "t1", "prompt": "hi"}', "{not json"],
    )
    with pytest.raises(ValueError, match=":2:"):
        load_tasks(path)


def test_invalid_task_reports_line_number(tmp_path) -> None:
    path = write_jsonl(
        tmp_path,
        ['{"id": "", "prompt": "hi"}'],
    )
    with pytest.raises(ValueError, match=":1:"):
        load_tasks(path)


def test_rejects_duplicate_task_ids(tmp_path) -> None:
    path = write_jsonl(
        tmp_path,
        [
            '{"id": "t1", "prompt": "a"}',
            "",
            '{"id": "t2", "prompt": "b"}',
            '{"id": "t1", "prompt": "c"}',
        ],
    )
    with pytest.raises(ValueError, match=r":4: duplicate task id 't1'.*line 1"):
        load_tasks(path)
