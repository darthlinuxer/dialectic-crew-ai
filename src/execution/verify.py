"""Task verification logic for execution plans."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from schemas import UserStoryExecutionPlan, PRDSchema, ImplementationTask

from dialectic.output_paths import resolve_prd_output_dir
from dialectic.prd_flow import OUTPUT_DIR as PRD_OUTPUT_DIR
from dialectic.target import resolve_active_project_root, temporary_working_directory
from dialectic.vision import VisionContext
from execution.validation_gate import run_stack_validation_gate
from execution.status import (
    STATUS_ICONS,
    find_task,
    load_plan,
    mark_task,
    save_plan,
    show_status,
    update_task_status,
    update_user_story_status,
)
from execution.verify_runtime import build_verification_crew


__all__ = [
    "show_status",
    "mark_task",
    "verify_task",
    "verify_user_story",
    "update_task_status",
    "update_user_story_status",
]


DEFAULT_VERIFICATION_SCORE = float(os.getenv("MIN_QUALITY_SCORE", "7.5"))


# ---------------------------------------------------------------------------
# Verify task with LLM (acceptance criteria check)
# ---------------------------------------------------------------------------

def _load_prd_for_plan(plan: UserStoryExecutionPlan, prd_path: str | None) -> PRDSchema | None:
    """Try to load the PRD that contains the user story for this plan."""
    if prd_path:
        with open(prd_path, "r", encoding="utf-8") as f:
            return PRDSchema.model_validate(json.load(f))
    if plan.source_prd_path and os.path.exists(plan.source_prd_path):
        with open(plan.source_prd_path, "r", encoding="utf-8") as f:
            return PRDSchema.model_validate(json.load(f))
    if PRD_OUTPUT_DIR == "prd_output":
        base = resolve_prd_output_dir(VisionContext.PROJECT)
    else:
        base = Path(PRD_OUTPUT_DIR)
    if not base.exists():
        return None
    jsons = list(base.glob("PRD_*.json"))
    if not jsons:
        return None
    latest = max(jsons, key=lambda p: p.stat().st_mtime)
    with open(latest, "r", encoding="utf-8") as f:
        return PRDSchema.model_validate(json.load(f))


def _extract_acceptance_criteria(
    plan: UserStoryExecutionPlan,
    prd: PRDSchema | None,
) -> list[str]:
    """Extract PRD acceptance criteria for the user story in this plan."""
    if not prd:
        return []
    us_id_norm = plan.user_story_id.strip().upper().replace("-", "").replace("_", "")
    for us in prd.user_stories:
        id_norm = us.id.strip().upper().replace("-", "").replace("_", "")
        if id_norm == us_id_norm:
            return us.acceptance_criteria
    return []


# ---------------------------------------------------------------------------
# Core verification (reusable by both CLI and execution flow)
# ---------------------------------------------------------------------------

def _run_verification(
    task: ImplementationTask,
    acceptance_criteria: list[str] | None = None,
    vision_context: VisionContext | None = None,
) -> dict:
    """
    Run LLM-based verification on a single task. Pure logic, no plan I/O.

    Returns dict with keys: task_id, verified, score, notes.
    """
    from schemas import ValidationOutput

    ctx = vision_context or VisionContext.PROJECT
    crew = build_verification_crew(
        task=task,
        acceptance_criteria=acceptance_criteria,
        vision_context=ctx,
    )
    with temporary_working_directory(resolve_active_project_root()):
        result = crew.kickoff()

    validation: ValidationOutput | None = None
    pydantic_result = getattr(result, "pydantic", None)
    if isinstance(pydantic_result, ValidationOutput):
        validation = pydantic_result
    else:
        tasks_out = getattr(result, "tasks_output", None) or []
        if tasks_out:
            last_p = getattr(tasks_out[-1], "pydantic", None)
            if isinstance(last_p, ValidationOutput):
                validation = last_p

    if validation is None:
        raw = getattr(result, "raw", str(result))
        return {
            "task_id": task.id,
            "verified": False,
            "score": 0.0,
            "notes": f"Failed to obtain structured result. Raw: {raw[:500]}",
        }

    verified = validation.quality_score >= DEFAULT_VERIFICATION_SCORE
    notes = validation.final_validation_notes
    if verified:
        gate = run_stack_validation_gate("story")
        verified = gate.verified
        notes = _join_notes(notes, gate.notes)
    return {
        "task_id": task.id,
        "verified": verified,
        "score": validation.quality_score,
        "notes": notes,
    }


def _join_notes(*parts: str) -> str:
    return " | ".join(part for part in parts if part)


# ---------------------------------------------------------------------------
# CLI-facing: verify single task
# ---------------------------------------------------------------------------

def verify_task(
    task_id: str,
    plan_path: str | None = None,
    prd_path: str | None = None,
) -> dict:
    """
    Verify task completion using an LLM agent that checks:
    1. Task description fulfillment (files exist, code correct)
    2. Acceptance criteria from PRD (if available)

    Updates plan status based on verification result.
    """
    plan, resolved = load_plan(plan_path)
    task = find_task(plan, task_id)

    prd = _load_prd_for_plan(plan, prd_path)
    acceptance_criteria = _extract_acceptance_criteria(plan, prd)

    print(f"\n  Verifying {task.id} — {task.title}...")
    vr = _run_verification(task, acceptance_criteria)

    new_status: Literal["completed", "failed"] = "completed" if vr["verified"] else "failed"
    task.status = new_status
    task.verification_notes = vr["notes"]
    if vr["verified"]:
        task.completed_at = datetime.now().isoformat(timespec="seconds")

    save_plan(plan, resolved)

    icon = STATUS_ICONS.get(new_status, "[ ]")
    print(f"\n  {icon} {task.id} — score: {vr['score']}/10")
    print(f"      Status: {new_status}")
    print(f"      Notes: {vr['notes'][:300]}")

    return {
        "task_id": task.id,
        "verified": vr["verified"],
        "score": vr["score"],
        "status": new_status,
        "notes": vr["notes"],
        "plan_path": resolved,
    }


# ---------------------------------------------------------------------------
# Verify all tasks in a user story and update story-level status
# ---------------------------------------------------------------------------

def verify_user_story(
    plan_path: str | None = None,
    prd_path: str | None = None,
) -> dict:
    """
    Verify all completed tasks against PRD acceptance criteria and compute
    user story-level status. Used both by the execution flow and the CLI.

    Returns dict with story_status, verified_tasks, failed_tasks, etc.
    """
    plan, resolved = load_plan(plan_path)
    prd = _load_prd_for_plan(plan, prd_path)
    acceptance_criteria = _extract_acceptance_criteria(plan, prd)

    completed_tasks = [t for t in plan.tasks if t.status == "completed"]
    failed_before = [t.id for t in plan.tasks if t.status == "failed"]

    if not completed_tasks and not failed_before:
        plan.status = "pending"
        plan.completed_at = None
        save_plan(plan, resolved)
        return {
            "plan_path": resolved,
            "story_status": "pending",
            "verified_tasks": [],
            "failed_verification_tasks": [],
            "already_failed_tasks": failed_before,
        }

    print(f"\n{'='*60}")
    print(f"  Verifying user story: {plan.user_story_id} — {plan.user_story_title}")
    print(f"  Tasks to verify: {len(completed_tasks)}")
    print(f"{'='*60}")

    verified_ids: list[str] = []
    failed_verification_ids: list[str] = []

    for task in completed_tasks:
        print(f"\n  Verifying {task.id} — {task.title}...")
        vr = _run_verification(task, acceptance_criteria)

        if vr["verified"]:
            verified_ids.append(task.id)
            task.verification_notes = f"[auto-verified] {vr['notes']}"
            icon = STATUS_ICONS["completed"]
        else:
            failed_verification_ids.append(task.id)
            task.status = "failed"
            task.verification_notes = f"[post-verify failed] {vr['notes']}"
            icon = STATUS_ICONS["failed"]

        print(f"  {icon} {task.id} — score: {vr['score']}/10")

    total = len(plan.tasks)
    all_failed = failed_before + failed_verification_ids
    total_verified = len(verified_ids)

    if total_verified == total:
        plan.status = "completed"
        plan.completed_at = datetime.now().isoformat(timespec="seconds")
    elif total_verified > 0:
        plan.status = "partially_completed"
        plan.completed_at = None
    else:
        plan.status = "failed"
        plan.completed_at = None

    save_plan(plan, resolved)

    icon = STATUS_ICONS.get(plan.status, "[ ]")
    print(f"\n  {icon} Story {plan.user_story_id}: {plan.status}")
    print(f"      Verified: {verified_ids}")
    if all_failed:
        print(f"      Failed:   {all_failed}")

    return {
        "plan_path": resolved,
        "story_status": plan.status,
        "verified_tasks": verified_ids,
        "failed_verification_tasks": failed_verification_ids,
        "already_failed_tasks": failed_before,
    }
