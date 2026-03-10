"""
Task verification and status tracking for execution plans.

Provides:
- show_status(): display task/story completion table
- mark_task(): manually set task status
- verify_task(): use LLM agent to verify a single task's acceptance criteria
- verify_user_story(): verify all completed tasks and update story-level status
- update_task_status(): programmatic task status update with persistence
- update_user_story_status(): programmatic story status update with persistence
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from schemas import UserStoryExecutionPlan, PRDSchema, ImplementationTask

from dialectic.prd_flow import OUTPUT_DIR as PRD_OUTPUT_DIR

_STORY_STATUS = Literal[
    "pending", "in_progress", "completed", "partially_completed", "failed"
]
DEFAULT_VERIFICATION_SCORE = float(os.getenv("MIN_QUALITY_SCORE", "7.5"))


# ---------------------------------------------------------------------------
# Plan I/O
# ---------------------------------------------------------------------------

def _find_latest_plan() -> Path:
    base = Path(PRD_OUTPUT_DIR)
    if not base.exists():
        raise FileNotFoundError(f"Directory {PRD_OUTPUT_DIR} not found.")
    jsons = list(base.glob("exec_*.json"))
    if not jsons:
        raise FileNotFoundError(f"No plan found in {PRD_OUTPUT_DIR}/ (expected exec_*.json)")
    return max(jsons, key=lambda p: p.stat().st_mtime)


def load_plan(plan_path: str | None) -> tuple[UserStoryExecutionPlan, str]:
    """Load plan from file. Returns (plan, resolved_path)."""
    if plan_path is None or plan_path == "--latest":
        path = str(_find_latest_plan())
    else:
        path = plan_path
    if not os.path.exists(path):
        raise FileNotFoundError(f"Plan not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return UserStoryExecutionPlan.model_validate(data), path


def save_plan(plan: UserStoryExecutionPlan, path: str) -> None:
    """Persist plan back to JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan.model_dump(), f, indent=2, ensure_ascii=False)


def _find_task(plan: UserStoryExecutionPlan, task_id: str) -> ImplementationTask:
    norm = task_id.strip().upper()
    for t in plan.tasks:
        if t.id.upper() == norm:
            return t
    available = [t.id for t in plan.tasks]
    raise ValueError(f"Task '{task_id}' not found. Available: {available}")


# ---------------------------------------------------------------------------
# Status display
# ---------------------------------------------------------------------------

_STATUS_ICONS = {
    "pending": "[ ]",
    "in_progress": "[~]",
    "completed": "[x]",
    "failed": "[!]",
    "partially_completed": "[/]",
}


def show_status(plan_path: str | None = None) -> dict:
    """Display task and user story status table. Returns summary dict."""
    plan, resolved = load_plan(plan_path)

    story_icon = _STATUS_ICONS.get(plan.status, "[ ]")
    story_completed = f"  ({plan.completed_at})" if plan.completed_at else ""

    print(f"\n{'='*65}")
    print(f"  {story_icon} {plan.user_story_id} — {plan.user_story_title}")
    print(f"  Story status: {plan.status}{story_completed}")
    print(f"  Score: {plan.quality_score}/10.0  |  Plan: {resolved}")
    print(f"{'='*65}")

    counts = {"pending": 0, "in_progress": 0, "completed": 0, "failed": 0}
    for t in sorted(plan.tasks, key=lambda x: (x.order, x.id)):
        icon = _STATUS_ICONS.get(t.status, "[ ]")
        deps = f"  (deps: {', '.join(t.dependencies)})" if t.dependencies else ""
        notes = f"  -- {t.verification_notes}" if t.verification_notes else ""
        completed = f"  ({t.completed_at})" if t.completed_at else ""
        print(f"  {icon} {t.id} — {t.title}{deps}{completed}{notes}")
        counts[t.status] = counts.get(t.status, 0) + 1

    total = len(plan.tasks)
    done = counts["completed"]
    print(f"\n  Progress: {done}/{total} completed", end="")
    if counts["failed"]:
        print(f", {counts['failed']} failed", end="")
    if counts["in_progress"]:
        print(f", {counts['in_progress']} in progress", end="")
    print(f"\n{'='*65}\n")

    return {
        "plan_path": resolved,
        "total": total,
        "story_status": plan.status,
        **counts,
    }


# ---------------------------------------------------------------------------
# Mark task
# ---------------------------------------------------------------------------

def mark_task(
    task_id: str,
    status: Literal["pending", "in_progress", "completed", "failed"],
    plan_path: str | None = None,
    notes: str = "",
) -> dict:
    """Manually set task status and persist."""
    plan, resolved = load_plan(plan_path)
    task = _find_task(plan, task_id)

    task.status = status
    if notes:
        task.verification_notes = notes
    if status == "completed":
        task.completed_at = datetime.now().isoformat(timespec="seconds")
    elif status == "pending":
        task.completed_at = None

    save_plan(plan, resolved)
    icon = _STATUS_ICONS.get(status, "[ ]")
    print(f"  {icon} {task.id} — {task.title} -> {status}")
    if notes:
        print(f"      Notes: {notes}")
    return {"task_id": task.id, "status": status, "plan_path": resolved}


# ---------------------------------------------------------------------------
# Update task status (programmatic, used by dialectic_execution)
# ---------------------------------------------------------------------------

def update_task_status(
    plan_path: str,
    task_id: str,
    status: Literal["pending", "in_progress", "completed", "failed"],
    notes: str = "",
) -> None:
    """Update task status in-place and save. Used by execution engine."""
    plan, resolved = load_plan(plan_path)
    task = _find_task(plan, task_id)
    task.status = status
    if notes:
        task.verification_notes = notes
    if status == "completed":
        task.completed_at = datetime.now().isoformat(timespec="seconds")
    save_plan(plan, resolved)


# ---------------------------------------------------------------------------
# Update user story status (programmatic)
# ---------------------------------------------------------------------------

def update_user_story_status(
    plan_path: str,
    status: _STORY_STATUS,
) -> None:
    """Update user story-level status in the plan and save."""
    plan, resolved = load_plan(plan_path)
    plan.status = status
    if status == "completed":
        plan.completed_at = datetime.now().isoformat(timespec="seconds")
    elif status in ("pending", "in_progress"):
        plan.completed_at = None
    save_plan(plan, resolved)


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
    vision_context: "VisionContext | None" = None,
) -> dict:
    """
    Run LLM-based verification on a single task. Pure logic, no plan I/O.

    Returns dict with keys: task_id, verified, score, notes.
    """
    from crewai import Task as CrewTask, Crew
    from dialectic.agents import create_validador_macro, crew_memory, vision_knowledge
    from dialectic.vision import VisionContext
    from dialectic.tools import file_read_tool
    from schemas import ValidationOutput

    ctx = vision_context or VisionContext.PROJECT

    ac_text = ""
    if acceptance_criteria:
        ac_text = (
            "\n\nACCEPTANCE CRITERIA for the User Story "
            "(verify whether this task contributes to meeting them):\n"
        )
        ac_text += "\n".join(f"- {ac}" for ac in acceptance_criteria)

    verify_agent = create_validador_macro(ctx)
    verify_agent.tools = [file_read_tool]

    verify_crew_task = CrewTask(
        description=f"""
Verify whether the task below was correctly implemented in the codebase.

TASK: {task.id} — {task.title}
DESCRIPTION: {task.description}

Use the file reading tools to verify whether:
1. The files/artifacts described in the task exist
2. The content is correct and aligned with the description
3. There are no obvious errors
{ac_text}

Respond with quality_score (0-10), consensus_reached (true if task is complete), and final_validation_notes explaining what was verified.
""",
        expected_output="ValidationOutput with quality_score, consensus_reached, final_validation_notes",
        agent=verify_agent,
        output_pydantic=ValidationOutput,
    )

    crew = Crew(
        agents=[verify_agent],
        tasks=[verify_crew_task],
        verbose=True,
        memory=crew_memory(ctx, "verify"),
        knowledge_sources=[vision_knowledge(ctx)],
    )
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
    return {
        "task_id": task.id,
        "verified": verified,
        "score": validation.quality_score,
        "notes": validation.final_validation_notes,
    }


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
    task = _find_task(plan, task_id)

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

    icon = _STATUS_ICONS.get(new_status, "[ ]")
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
            icon = _STATUS_ICONS["completed"]
        else:
            failed_verification_ids.append(task.id)
            task.status = "failed"
            task.verification_notes = f"[post-verify failed] {vr['notes']}"
            icon = _STATUS_ICONS["failed"]

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

    icon = _STATUS_ICONS.get(plan.status, "[ ]")
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
