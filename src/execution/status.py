"""Execution plan status display and persistence helpers."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from dialectic.output_paths import resolve_prd_output_dir
from dialectic.prd_flow import OUTPUT_DIR as PRD_OUTPUT_DIR
from dialectic.vision import VisionContext
from execution.plan_loader import find_latest_plan, load_plan as load_plan_file
from schemas import ImplementationTask, UserStoryExecutionPlan

STORY_STATUS = Literal[
    "pending", "in_progress", "completed", "partially_completed", "failed"
]

STATUS_ICONS = {
    "pending": "[ ]",
    "in_progress": "[~]",
    "completed": "[x]",
    "failed": "[!]",
    "partially_completed": "[/]",
}


def find_latest_plan_path() -> Path:
    if PRD_OUTPUT_DIR == "prd_output":
        return find_latest_plan(resolve_prd_output_dir(VisionContext.PROJECT))
    return find_latest_plan(PRD_OUTPUT_DIR)


def load_plan(plan_path: str | None) -> tuple[UserStoryExecutionPlan, str]:
    """Load plan from file and return `(plan, resolved_path)`."""
    if plan_path is None or plan_path == "--latest":
        path = str(find_latest_plan_path())
    else:
        path = plan_path
    if not os.path.exists(path):
        raise FileNotFoundError(f"Plan not found: {path}")
    return load_plan_file(path), path


def save_plan(plan: UserStoryExecutionPlan, path: str) -> None:
    with open(path, "w", encoding="utf-8") as file_handle:
        json.dump(plan.model_dump(), file_handle, indent=2, ensure_ascii=False)


def find_task(plan: UserStoryExecutionPlan, task_id: str) -> ImplementationTask:
    normalized = task_id.strip().casefold()
    for task in plan.tasks:
        if task.id.casefold() == normalized:
            return task
    available = [task.id for task in plan.tasks]
    raise ValueError(f"Task '{task_id}' not found. Available: {available}")


def show_status(plan_path: str | None = None) -> dict:
    plan, resolved = load_plan(plan_path)

    story_icon = STATUS_ICONS.get(plan.status, "[ ]")
    story_completed = f"  ({plan.completed_at})" if plan.completed_at else ""

    print(f"\n{'=' * 65}")
    print(f"  {story_icon} {plan.user_story_id} — {plan.user_story_title}")
    print(f"  Story status: {plan.status}{story_completed}")
    print(f"  Score: {plan.quality_score}/10.0  |  Plan: {resolved}")
    print(f"{'=' * 65}")

    counts = {"pending": 0, "in_progress": 0, "completed": 0, "failed": 0}
    for task in sorted(plan.tasks, key=lambda item: (item.order, item.id)):
        icon = STATUS_ICONS.get(task.status, "[ ]")
        dependencies = f"  (deps: {', '.join(task.dependencies)})" if task.dependencies else ""
        notes = f"  -- {task.verification_notes}" if task.verification_notes else ""
        completed = f"  ({task.completed_at})" if task.completed_at else ""
        print(f"  {icon} {task.id} — {task.title}{dependencies}{completed}{notes}")
        counts[task.status] = counts.get(task.status, 0) + 1

    total = len(plan.tasks)
    done = counts["completed"]
    print(f"\n  Progress: {done}/{total} completed", end="")
    if counts["failed"]:
        print(f", {counts['failed']} failed", end="")
    if counts["in_progress"]:
        print(f", {counts['in_progress']} in progress", end="")
    print(f"\n{'=' * 65}\n")

    return {
        "plan_path": resolved,
        "total": total,
        "story_status": plan.status,
        **counts,
    }


def mark_task(
    task_id: str,
    status: Literal["pending", "in_progress", "completed", "failed"],
    plan_path: str | None = None,
    notes: str = "",
) -> dict:
    plan, resolved = load_plan(plan_path)
    task = find_task(plan, task_id)

    task.status = status
    if notes:
        task.verification_notes = notes
    if status == "completed":
        task.completed_at = datetime.now().isoformat(timespec="seconds")
    elif status == "pending":
        task.completed_at = None

    save_plan(plan, resolved)
    icon = STATUS_ICONS.get(status, "[ ]")
    print(f"  {icon} {task.id} — {task.title} -> {status}")
    if notes:
        print(f"      Notes: {notes}")
    return {"task_id": task.id, "status": status, "plan_path": resolved}


def update_task_status(
    plan_path: str,
    task_id: str,
    status: Literal["pending", "in_progress", "completed", "failed"],
    notes: str = "",
) -> None:
    plan, resolved = load_plan(plan_path)
    task = find_task(plan, task_id)
    task.status = status
    if notes:
        task.verification_notes = notes
    if status == "completed":
        task.completed_at = datetime.now().isoformat(timespec="seconds")
    save_plan(plan, resolved)


def update_user_story_status(plan_path: str, status: STORY_STATUS) -> None:
    plan, resolved = load_plan(plan_path)
    plan.status = status
    if status == "completed":
        plan.completed_at = datetime.now().isoformat(timespec="seconds")
    elif status in ("pending", "in_progress"):
        plan.completed_at = None
    save_plan(plan, resolved)
