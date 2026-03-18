"""
Real plan execution with CrewAI and dialectic method.
Cycle per task: Implementer → Critic → Synthesizer → Validator, with retry until score >= threshold.

Flow per task (via TaskExecutionFlow — native CrewAI Flow):
  1. Dialectic cycle (implement → critique → synthesize → validate) with retries
  2. Post-execution verification (A) + acceptance criteria (B)
  3. If verify fails → independent re-implementation (C) via @router

Uses native CrewAI features:
- Flow with @start/@listen/@router for conditional control
- output_pydantic: structured output from Validator
- Task guardrails: automatic output validation
- Agent reasoning=True on independent verifier
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from dialectic.app_logging import log_context
from dialectic.output_paths import resolve_exec_output_dir, resolve_prd_output_dir
from dialectic.prd_flow import OUTPUT_DIR as PRD_OUTPUT_DIR
from dialectic.target import resolve_execution_root, temporary_working_directory
from dialectic.vision import VisionContext
from schemas import (
    ExecutionCheckpoint,
    TaskExecutionResult,
)
from execution.checkpoint import (
    checkpoint_path,
    load_checkpoint,
    save_checkpoint,
    upsert_task_result,
)
from execution.context_builder import build_task_context
from execution.dialectic_execution_support import (
    finalize_execution_report,
    post_verify_completed_tasks,
    prepare_resume_state,
)
from execution.plan_loader import find_latest_plan, load_plan as load_plan_file
from execution.task_flow import TaskExecutionFlow, _get_task_persistence
from execution.topological_sort import topological_sort
from execution.verify import (
    _extract_acceptance_criteria,
    _load_prd_for_plan,
    _run_verification,
    update_task_status,
    update_user_story_status,
)

logger = logging.getLogger(__name__)

EXEC_OUTPUT_DIR = "exec_output"
DEFAULT_MAX_RETRIES_PER_TASK = int(os.getenv("MAX_RETRIES_PER_TASK", "3"))
DEFAULT_MIN_SCORE = float(os.getenv("MIN_QUALITY_SCORE", "7.5"))


_topological_sort = topological_sort
_build_task_context = build_task_context
_checkpoint_path = checkpoint_path
_save_checkpoint = save_checkpoint
_load_checkpoint = load_checkpoint
_upsert_task_result = upsert_task_result


# ---------------------------------------------------------------------------
# Main execution orchestrator (uses TaskExecutionFlow per task)
# ---------------------------------------------------------------------------


# pylint: disable=too-many-locals,too-many-branches,too-many-statements
def run_dialectic_execution(
    plan_path: str | None = None,
    max_retries_per_task: int = DEFAULT_MAX_RETRIES_PER_TASK,
    output_dir: str | None = None,
    vision_context: VisionContext = VisionContext.PROJECT,
    resume_run_id: str | None = None,
) -> dict:
    """
    Execute the plan with native CrewAI Flow per task.

    Each task runs through TaskExecutionFlow:
      dialectic → @router → verify (A+B) → @router → reimplement (C) if needed

    The active vision document is loaded via TextFileKnowledgeSource on each
    Crew according to the provided VisionContext, not injected as raw text.
    """
    out_dir = (
        Path(output_dir) if output_dir else resolve_exec_output_dir(vision_context)
    )
    resumed_from_run_id = resume_run_id or None

    if resume_run_id:
        run_id = resume_run_id
        run_dir = out_dir / run_id
        checkpoint = _load_checkpoint(run_dir)
        path = (
            plan_path if plan_path not in {None, "--latest"} else checkpoint.plan_path
        )
        if path is None:
            raise FileNotFoundError("Execution checkpoint does not contain a plan path")
        if Path(path).resolve() != Path(checkpoint.plan_path).resolve():
            raise ValueError(
                "Resume run plan path does not match the persisted execution checkpoint"
            )
        vision_context = VisionContext(checkpoint.vision_context)
    else:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = out_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        checkpoint = None
        path = plan_path
        if path is None or path == "--latest":
            latest_dir = (
                resolve_prd_output_dir(vision_context)
                if PRD_OUTPUT_DIR == "prd_output"
                else Path(PRD_OUTPUT_DIR)
            )
            path = str(find_latest_plan(latest_dir))

    if path is None:
        raise FileNotFoundError("Execution plan path could not be resolved")

    resolved_plan_path = path

    if not os.path.exists(resolved_plan_path):
        raise FileNotFoundError(f"Plan not found: {resolved_plan_path}")

    plan = load_plan_file(resolved_plan_path)
    try:
        ordered_tasks = _topological_sort(plan.tasks)
    except ValueError as exc:
        raise ValueError(
            f"Execution plan {plan.user_story_id} has invalid task dependencies: {exc}"
        ) from exc

    if checkpoint is None:
        checkpoint = ExecutionCheckpoint(
            plan_id=plan.user_story_id,
            plan_title=plan.user_story_title,
            run_id=run_id,
            plan_path=str(Path(resolved_plan_path).resolve()),
            vision_context=vision_context.value,
            resumed_from_run_id=resumed_from_run_id,
        )
        _save_checkpoint(run_dir, checkpoint)

    existing_results = {result.task_id: result for result in checkpoint.task_results}

    with log_context(
        command="execute",
        phase="execution",
        run_id=run_id,
        story_id=plan.user_story_id,
        vision_context=vision_context.value,
    ):
        logger.info("Execution run started")

    try:
        update_user_story_status(resolved_plan_path, "in_progress")
    except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        logger.warning("Failed to set story status to in_progress: %s", exc)

    print(f"\n{'=' * 60}")
    print(f"Executing plan — {plan.user_story_id} {plan.user_story_title}")
    print(f"Tasks: {len(ordered_tasks)} | Retries/task: {max_retries_per_task}")
    print("Flow: dialectic → verify(A+B) → reimplement(C) → post-verify(PRD)")
    if resume_run_id:
        print(f"Resuming run id: {resume_run_id}")
    print(f"{'=' * 60}\n")

    if resume_run_id:
        existing_results, task_results, completed_outputs, failed_task_ids = (
            prepare_resume_state(checkpoint, existing_results, run_dir)
        )
    else:
        task_results = list(checkpoint.task_results)
        completed_outputs = dict(checkpoint.completed_outputs)
        failed_task_ids = set(checkpoint.failed_task_ids)

    for task in ordered_tasks:
        with log_context(phase="task", task_id=task.id):
            previous_result = existing_results.get(task.id)
            if previous_result is not None:
                status = "completed" if previous_result.success else "failed"
                logger.info("Reusing task result from checkpoint")
                print(
                    f"\n>>> Reusing {status} task {task.id} — {task.title} from checkpoint"
                )
                previous_summary = previous_result.output_summary
                if previous_result.success and previous_summary:
                    completed_outputs[task.id] = previous_summary
                if not previous_result.success:
                    failed_task_ids.add(task.id)
                continue

            unmet_deps = [d for d in task.dependencies if d in failed_task_ids]
            if unmet_deps:
                logger.warning("Skipping task because dependencies failed")
                print(
                    "\n>>> SKIPPING task "
                    f"{task.id} — {task.title} "
                    f"(failed deps: {', '.join(unmet_deps)})"
                )
                skip_result = TaskExecutionResult(
                    task_id=task.id,
                    title=task.title,
                    success=False,
                    score=0.0,
                    retry_count=0,
                    validation_notes=f"Skipped: dependencies failed: {unmet_deps}",
                )
                task_results = _upsert_task_result(task_results, skip_result)
                failed_task_ids.add(task.id)
                checkpoint.task_results = task_results
                checkpoint.failed_task_ids = sorted(failed_task_ids)
                _save_checkpoint(run_dir, checkpoint)
                try:
                    update_task_status(
                        resolved_plan_path,
                        task.id,
                        "failed",
                        notes=f"Skipped: dependencies failed: {unmet_deps}",
                    )
                except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                    logger.warning(
                        "Failed to update status for skipped %s: %s", task.id, exc
                    )
                continue

            task_output_dir = resolve_execution_root()
            logger.info("Executing task")
            print(f"\n>>> Executing task {task.id} — {task.title}")

            try:
                update_task_status(resolved_plan_path, task.id, "in_progress")
            except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                logger.warning("Failed to set %s to in_progress: %s", task.id, exc)

            context_str = _build_task_context(plan, completed_outputs, task)

            try:
                flow = TaskExecutionFlow(_get_task_persistence())
                flow_id = checkpoint.task_flow_ids.get(task.id, flow.flow_id)
                checkpoint.task_flow_ids[task.id] = flow_id
                _save_checkpoint(run_dir, checkpoint)

                with log_context(flow_id=flow_id):
                    with temporary_working_directory(resolve_execution_root()):
                        flow_result = flow.kickoff(
                            inputs={
                                "id": flow_id,
                                "task_id": task.id,
                                "task_title": task.title,
                                "task_description": task.description,
                                "context_str": context_str,
                                "output_dir": str(task_output_dir),
                                "acceptance_checks": task.acceptance_checks,
                                "min_score": DEFAULT_MIN_SCORE,
                                "max_retries": max_retries_per_task,
                                "vision_context": vision_context.value,
                            }
                        )

                if isinstance(flow_result, TaskExecutionResult):
                    result = flow_result
                else:
                    result = TaskExecutionResult(
                        task_id=task.id,
                        title=task.title,
                        success=flow.state.dialectic_success,
                        score=flow.state.dialectic_score,
                        retry_count=flow.state.dialectic_retries,
                        output_paths=[str(task_output_dir)]
                        if task_output_dir.exists()
                        else [],
                        validation_notes=flow.state.dialectic_notes,
                        output_summary=flow.state.impl_output[:5000],
                        execution_phases=flow.state.phases_executed,
                    )

            except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                logger.exception("Task execution raised an exception")
                print(f"   {task.id} failed with exception: {exc}")
                result = TaskExecutionResult(
                    task_id=task.id,
                    title=task.title,
                    success=False,
                    score=0.0,
                    retry_count=max_retries_per_task,
                    output_paths=[],
                    validation_notes=f"Exception: {exc}",
                    output_summary="",
                )

        task_results = _upsert_task_result(task_results, result)

        if result.success:
            phases = (
                " → ".join(result.execution_phases)
                if result.execution_phases
                else "dialectic"
            )
            print(f"   {task.id} APPROVED ({result.score}/10) [{phases}]")
            completed_outputs[task.id] = (
                result.output_summary or f"Task completed. Score: {result.score}"
            )
            try:
                update_task_status(
                    resolved_plan_path,
                    task.id,
                    "completed",
                    notes=f"Score: {result.score}/10 [{phases}]. {result.validation_notes[:200]}",
                )
            except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                logger.warning(
                    "Failed to update status for completed %s: %s", task.id, exc
                )
        else:
            phases = (
                " → ".join(result.execution_phases)
                if result.execution_phases
                else "dialectic"
            )
            print(f"   {task.id} FAILED ({result.score}/10) [{phases}]")
            failed_task_ids.add(task.id)
            try:
                update_task_status(
                    resolved_plan_path,
                    task.id,
                    "failed",
                    notes=f"Score: {result.score}/10 [{phases}]. {result.validation_notes[:200]}",
                )
            except Exception as exc:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                logger.warning(
                    "Failed to update status for failed %s: %s", task.id, exc
                )

        checkpoint.task_results = task_results
        checkpoint.completed_outputs = completed_outputs
        checkpoint.failed_task_ids = sorted(failed_task_ids)
        _save_checkpoint(run_dir, checkpoint)

    plan, verified_ids, failed_verification_ids = post_verify_completed_tasks(
        plan_path=resolved_plan_path,
        task_results=task_results,
        vision_context=vision_context,
        load_prd_for_plan=_load_prd_for_plan,
        extract_acceptance_criteria=_extract_acceptance_criteria,
        run_verification=_run_verification,
    )
    report, story_status, report_path = finalize_execution_report(
        run_dir=run_dir,
        plan_path=resolved_plan_path,
        checkpoint=checkpoint,
        resumed_from_run_id=resumed_from_run_id,
        vision_context=vision_context,
        task_results=task_results,
        verified_ids=verified_ids,
        failed_verification_ids=failed_verification_ids,
    )
    overall_success = report.overall_success
    all_failed = report.failed_verification_tasks

    print(f"\n{'=' * 60}")
    print(f"Story {plan.user_story_id}: {story_status}")
    print(f"  Verified: {verified_ids}")
    if all_failed:
        print(f"  Failed:   {all_failed}")
    print(f"{'=' * 60}")

    return {
        "run_id": run_id,
        "output_path": str(run_dir),
        "report_path": str(report_path),
        "plan_id": plan.user_story_id,
        "plan_title": plan.user_story_title,
        "overall_success": overall_success,
        "story_status": story_status,
        "verified_tasks": verified_ids,
        "failed_verification_tasks": all_failed,
        "task_flow_ids": checkpoint.task_flow_ids,
        "report": report.model_dump(),
    }
