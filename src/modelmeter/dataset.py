"""Task dataset loading.

Reads JSONL files (one Task object per line) and validates each entry.
IO is confined to this module; the runner consumes validated Task lists.
"""

from __future__ import annotations

import json
from pathlib import Path

from modelmeter.config import Task


def load_tasks(path: Path) -> list[Task]:
    """Load tasks from a JSONL file.

    Raises:
        FileNotFoundError: if path does not exist.
        ValueError: if any line is not a valid Task or reuses a task id; message
            includes the 1-based line number.
    """
    text = path.read_text(encoding="utf-8")
    tasks: list[Task] = []
    first_seen: dict[str, int] = {}
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
        try:
            tasks.append(Task.model_validate(raw))
        except Exception as exc:  # noqa: BLE001 - report pydantic errors with location
            raise ValueError(f"{path}:{line_no}: invalid task: {exc}") from exc
        task_id = tasks[-1].id
        if task_id in first_seen:
            raise ValueError(
                f"{path}:{line_no}: duplicate task id {task_id!r} "
                f"(first used on line {first_seen[task_id]})"
            )
        first_seen[task_id] = line_no
    return tasks
