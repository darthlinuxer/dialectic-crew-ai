"""Shared helpers for locating and loading execution plans."""

from __future__ import annotations

import json
from pathlib import Path

from dialectic.output_paths import resolve_prd_output_dir
from dialectic.prd_flow import OUTPUT_DIR as PRD_OUTPUT_DIR
from dialectic.vision import VisionContext
from schemas import UserStoryExecutionPlan


def find_latest_plan(output_dir: str | Path = PRD_OUTPUT_DIR) -> Path:
    """Find the most recent execution plan JSON file in *output_dir*."""
    if str(output_dir) == PRD_OUTPUT_DIR:
        base = resolve_prd_output_dir(VisionContext.PROJECT)
    else:
        base = Path(output_dir)
    if not base.exists():
        raise FileNotFoundError(f"Directory {base} not found.")

    jsons = list(base.glob("exec_*.json"))
    if not jsons:
        raise FileNotFoundError(
            f"No execution plan found in {base}/ (expected exec_*.json)"
        )

    return max(jsons, key=lambda path: path.stat().st_mtime)


def load_plan(plan_path: str | Path) -> UserStoryExecutionPlan:
    """Load and validate a user-story execution plan from JSON."""
    path = Path(plan_path)
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return UserStoryExecutionPlan.model_validate(data)