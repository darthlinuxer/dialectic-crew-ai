"""Support helpers for execution resume, post-verification, and reporting."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable, Literal

from dialectic.app_logging import log_context
from dialectic.vision import VisionContext, get_vision_hash
from schemas import (
    ExecutionCheckpoint,
    ExecutionReport,
    TaskExecutionResult,
    UserStoryExecutionPlan,
)

from .checkpoint import save_checkpoint
from .plan_loader import load_plan as load_plan_file
from .runner import _artifact_markdown
from .verify import (
    update_task_status,
    update_user_story_status,
)

logger = logging.getLogger(__name__)


def prepare_resume_state(
    checkpoint: ExecutionCheckpoint,
    existing_results: dict[str, TaskExecutionResult],
    run_dir: Path,
) -> tuple[
    dict[str, TaskExecutionResult],
    list[TaskExecutionResult],
    dict[str, str],
    set[str],
]:
    """Drop failed checkpoint artifacts and keep only reusable successful results."""
    reusable_results = {
        task_id: result
        for task_id, result in existing_results.items()
        if result.success
    }
    checkpoint.task_results = list(reusable_results.values())
    checkpoint.task_flow_ids = {
        task_id: flow_id
        for task_id, flow_id in checkpoint.task_flow_ids.items()
        if task_id in reusable_results
    }
    checkpoint.completed_outputs = {
        task_id: output
        for task_id, output in checkpoint.completed_outputs.items()
        if task_id in reusable_results
    }
    checkpoint.failed_task_ids = []
    save_checkpoint(run_dir, checkpoint)
    return (
        reusable_results,
        list(reusable_results.values()),
        dict(checkpoint.completed_outputs),
        set(),
    )


# pylint: disable=too-many-arguments,too-many-locals
def post_verify_completed_tasks(
    *,
    plan_path: str,
    task_results: list[TaskExecutionResult],
    vision_context: VisionContext,
    load_prd_for_plan: Callable[..., Any],
    extract_acceptance_criteria: Callable[..., list[Any]],
    run_verification: Callable[..., dict[str, object]],
) -> tuple[UserStoryExecutionPlan, list[str], list[str]]:
    """Run post-execution verification for every successfully completed task."""
    plan = load_plan_file(plan_path)
    completed_task_ids = [result.task_id for result in task_results if result.success]
    verified_ids: list[str] = []
    failed_verification_ids: list[str] = []

    if completed_task_ids:
        print(f"\n{'=' * 60}")
        print("Post-execution verification against PRD acceptance criteria")
        print(f"Tasks to verify: {len(completed_task_ids)}")
        print(f"{'=' * 60}")

        prd = load_prd_for_plan(plan, None)
        acceptance_criteria = extract_acceptance_criteria(plan, prd)

        for task_id in completed_task_ids:
            with log_context(phase="post_verify", task_id=task_id):
                matched_task = next(
                    (candidate for candidate in plan.tasks if candidate.id == task_id),
                    None,
                )
                if matched_task is None:
                    continue
                print(f"\n  Post-verifying {matched_task.id} — {matched_task.title}...")
                try:
                    verification_result = run_verification(
                        matched_task,
                        acceptance_criteria,
                        vision_context,
                    )
                    _apply_post_verification_result(
                        plan_path,
                        matched_task.id,
                        verification_result,
                        verified_ids,
                        failed_verification_ids,
                    )
                except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                    failed_verification_ids.append(task_id)
                    logger.exception("Post-verification raised an exception")
                    print(f"   {task_id} verification error: {exc}")

    return plan, verified_ids, failed_verification_ids


def _apply_post_verification_result(
    plan_path: str,
    task_id: str,
    verification_result: dict[str, object],
    verified_ids: list[str],
    failed_verification_ids: list[str],
) -> None:
    """Persist the outcome of a single post-verification result."""
    score = verification_result["score"]
    notes = str(verification_result["notes"])
    if verification_result["verified"]:
        verified_ids.append(task_id)
        logger.info("Post-verification passed")
        print(f"   {task_id} VERIFIED (score: {score}/10)")
        _update_post_verification_status(
            plan_path,
            task_id,
            "completed",
            f"[post-verified] score: {score}/10. {notes[:200]}",
        )
        return

    failed_verification_ids.append(task_id)
    logger.warning("Post-verification failed")
    print(f"   {task_id} VERIFICATION FAILED (score: {score}/10)")
    _update_post_verification_status(
        plan_path,
        task_id,
        "failed",
        f"[post-verify failed] score: {score}/10. {notes[:200]}",
    )


def _update_post_verification_status(
    plan_path: str,
    task_id: str,
    status: Literal["completed", "failed"],
    notes: str,
) -> None:
    """Best-effort task status update for post-verification results."""
    try:
        update_task_status(plan_path, task_id, status, notes=notes)
    except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        logger.warning(
            "Failed to update %s status for %s: %s",
            status,
            task_id,
            exc,
        )


# pylint: disable=too-many-arguments,too-many-locals
def finalize_execution_report(
    *,
    run_dir: Path,
    plan_path: str,
    checkpoint: ExecutionCheckpoint,
    resumed_from_run_id: str | None,
    vision_context: VisionContext,
    task_results: list[TaskExecutionResult],
    verified_ids: list[str],
    failed_verification_ids: list[str],
) -> tuple[
    ExecutionReport, Literal["completed", "partially_completed", "failed"], Path
]:
    """Persist the final report and return report metadata for the run."""
    plan = load_plan_file(plan_path)
    total_tasks = len(plan.tasks)
    already_failed = [result.task_id for result in task_results if not result.success]
    all_failed = already_failed + failed_verification_ids
    total_verified = len(verified_ids)

    story_status: Literal["completed", "partially_completed", "failed"]
    if total_verified == total_tasks:
        story_status = "completed"
    elif total_verified > 0:
        story_status = "partially_completed"
    else:
        story_status = "failed"

    try:
        update_user_story_status(plan_path, story_status)
    except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        logger.warning("Failed to update story status to %s: %s", story_status, exc)

    report = ExecutionReport(
        plan_id=plan.user_story_id,
        plan_title=plan.user_story_title,
        run_id=checkpoint.run_id,
        plan_path=str(Path(plan_path).resolve()),
        vision_hash=plan.vision_hash or get_vision_hash(vision_context),
        source_roadmap_path=plan.source_roadmap_path,
        source_roadmap_label=plan.source_roadmap_label,
        source_roadmap_key=plan.source_roadmap_key,
        task_results=task_results,
        overall_success=total_verified == total_tasks,
        verified_tasks=verified_ids,
        failed_verification_tasks=all_failed,
        task_flow_ids=checkpoint.task_flow_ids,
        resumed_from_run_id=resumed_from_run_id,
    )

    report_path = run_dir / "report.json"
    report_path.write_text(
        json.dumps(report.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    safe_id = plan.user_story_id.replace(" ", "_")
    spec_path = run_dir / f"spec_{safe_id}_{checkpoint.run_id}.md"
    spec_path.write_text(_artifact_markdown(plan), encoding="utf-8")
    return report, story_status, report_path
