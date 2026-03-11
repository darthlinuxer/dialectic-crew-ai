"""Checkpoint persistence helpers for execution runs."""

from __future__ import annotations

import json
from pathlib import Path

from schemas import ExecutionCheckpoint, TaskExecutionResult


def checkpoint_path(run_dir: Path) -> Path:
    return run_dir / "checkpoint.json"


def save_checkpoint(run_dir: Path, checkpoint: ExecutionCheckpoint) -> None:
    path = checkpoint_path(run_dir)
    with open(path, "w", encoding="utf-8") as file_handle:
        json.dump(checkpoint.model_dump(), file_handle, indent=2, ensure_ascii=False)


def load_checkpoint(run_dir: Path) -> ExecutionCheckpoint:
    path = checkpoint_path(run_dir)
    if not path.exists():
        raise FileNotFoundError(f"Execution checkpoint not found: {path}")
    with open(path, "r", encoding="utf-8") as file_handle:
        data = json.load(file_handle)
    return ExecutionCheckpoint.model_validate(data)


def upsert_task_result(
    task_results: list[TaskExecutionResult],
    result: TaskExecutionResult,
) -> list[TaskExecutionResult]:
    remaining = [item for item in task_results if item.task_id != result.task_id]
    remaining.append(result)
    return remaining
