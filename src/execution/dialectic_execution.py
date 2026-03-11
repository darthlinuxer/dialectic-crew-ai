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

import json
import logging
import os
from collections import deque
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

from dialectic.prd_flow import OUTPUT_DIR as PRD_OUTPUT_DIR
from schemas import (
    ImplementationTask,
    UserStoryExecutionPlan,
    TaskExecutionResult,
    ExecutionReport,
    ExecutionCheckpoint,
)
from execution.runner import _artifact_markdown
from execution.plan_loader import find_latest_plan, load_plan as load_plan_file
from execution.verify import (
    update_task_status,
    update_user_story_status,
    _run_verification,
    _load_prd_for_plan,
    _extract_acceptance_criteria,
    load_plan,
)
from execution.task_flow import TaskExecutionFlow, _get_task_persistence
from dialectic.vision import VisionContext, get_vision_hash

EXEC_OUTPUT_DIR = "exec_output"
DEFAULT_MAX_RETRIES_PER_TASK = int(os.getenv("MAX_RETRIES_PER_TASK", "3"))
DEFAULT_MIN_SCORE = float(os.getenv("MIN_QUALITY_SCORE", "7.5"))


# ---------------------------------------------------------------------------
# Plan loading / topological sort
# ---------------------------------------------------------------------------

def _topological_sort(tasks: list[ImplementationTask]) -> list[ImplementationTask]:
    by_id = {t.id: t for t in tasks}
    in_degree = {t.id: 0 for t in tasks}
    for t in tasks:
        for dep in t.dependencies:
            if dep in by_id:
                in_degree[t.id] += 1
    queue = deque(tid for tid, d in in_degree.items() if d == 0)
    result: list[ImplementationTask] = []
    while queue:
        tid = queue.popleft()
        result.append(by_id[tid])
        for t in tasks:
            if tid in t.dependencies:
                in_degree[t.id] -= 1
                if in_degree[t.id] == 0:
                    queue.append(t.id)
    if len(result) != len(tasks):
        return sorted(tasks, key=lambda x: (x.order, x.id))
    return result


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def _build_task_context(
    plan: UserStoryExecutionPlan,
    completed_outputs: dict[str, str],
    current_task: ImplementationTask,
) -> str:
    lines = [
        "## Execution plan",
        "",
        f"User Story: {plan.user_story_id} — {plan.user_story_title}",
        f"Approach: {plan.approach_summary}",
        "",
        "## Previously executed tasks (outputs)",
        "",
    ]
    if not completed_outputs:
        lines.append("No previous tasks yet.")
    else:
        for tid, out in completed_outputs.items():
            lines.append(f"### {tid}")
            lines.append(out[:1500] + ("..." if len(out) > 1500 else ""))
            lines.append("")
    lines.extend([
        "## Current task to implement",
        "",
        f"**{current_task.id} — {current_task.title}**",
        "",
        current_task.description,
    ])
    return "\n".join(lines)


def _checkpoint_path(run_dir: Path) -> Path:
    return run_dir / "checkpoint.json"


def _save_checkpoint(run_dir: Path, checkpoint: ExecutionCheckpoint) -> None:
    path = _checkpoint_path(run_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(checkpoint.model_dump(), f, indent=2, ensure_ascii=False)


def _load_checkpoint(run_dir: Path) -> ExecutionCheckpoint:
    path = _checkpoint_path(run_dir)
    if not path.exists():
        raise FileNotFoundError(f"Execution checkpoint not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ExecutionCheckpoint.model_validate(data)


def _upsert_task_result(
    task_results: list[TaskExecutionResult],
    result: TaskExecutionResult,
) -> list[TaskExecutionResult]:
    remaining = [item for item in task_results if item.task_id != result.task_id]
    remaining.append(result)
    return remaining


# ---------------------------------------------------------------------------
# Main execution orchestrator (uses TaskExecutionFlow per task)
# ---------------------------------------------------------------------------

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
    out_dir = Path(output_dir or EXEC_OUTPUT_DIR)
    resumed_from_run_id = resume_run_id or None

    if resume_run_id:
        run_id = resume_run_id
        run_dir = out_dir / run_id
        checkpoint = _load_checkpoint(run_dir)
        path = plan_path if plan_path not in {None, "--latest"} else checkpoint.plan_path
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
            path = str(find_latest_plan(PRD_OUTPUT_DIR))

    if not os.path.exists(path):
        raise FileNotFoundError(f"Plan not found: {path}")

    plan = load_plan_file(path)
    ordered_tasks = _topological_sort(plan.tasks)

    if checkpoint is None:
        checkpoint = ExecutionCheckpoint(
            plan_id=plan.user_story_id,
            plan_title=plan.user_story_title,
            run_id=run_id,
            plan_path=str(Path(path).resolve()),
            vision_context=vision_context.value,
            resumed_from_run_id=resumed_from_run_id,
        )
        _save_checkpoint(run_dir, checkpoint)

    existing_results = {result.task_id: result for result in checkpoint.task_results}

    try:
        update_user_story_status(path, "in_progress")
    except Exception as exc:
        logger.warning("Failed to set story status to in_progress: %s", exc)

    print(f"\n{'='*60}")
    print(f"Executing plan — {plan.user_story_id} {plan.user_story_title}")
    print(f"Tasks: {len(ordered_tasks)} | Retries/task: {max_retries_per_task}")
    print(f"Flow: dialectic → verify(A+B) → reimplement(C) → post-verify(PRD)")
    if resume_run_id:
        print(f"Resuming run id: {resume_run_id}")
    print(f"{'='*60}\n")

    task_results: list[TaskExecutionResult] = list(checkpoint.task_results)
    completed_outputs: dict[str, str] = dict(checkpoint.completed_outputs)
    failed_task_ids: set[str] = set(checkpoint.failed_task_ids)

    for task in ordered_tasks:
        previous_result = existing_results.get(task.id)
        if previous_result is not None:
            status = "completed" if previous_result.success else "failed"
            print(f"\n>>> Reusing {status} task {task.id} — {task.title} from checkpoint")
            if previous_result.success and previous_result.output_summary:
                completed_outputs[task.id] = previous_result.output_summary
            if not previous_result.success:
                failed_task_ids.add(task.id)
            continue

        unmet_deps = [d for d in task.dependencies if d in failed_task_ids]
        if unmet_deps:
            print(f"\n>>> SKIPPING task {task.id} — {task.title} (failed deps: {', '.join(unmet_deps)})")
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
                update_task_status(path, task.id, "failed", notes=f"Skipped: dependencies failed: {unmet_deps}")
            except Exception as exc:
                logger.warning("Failed to update status for skipped %s: %s", task.id, exc)
            continue

        task_output_dir = run_dir / f"{task.id}_output"
        task_output_dir.mkdir(exist_ok=True)
        print(f"\n>>> Executing task {task.id} — {task.title}")

        try:
            update_task_status(path, task.id, "in_progress")
        except Exception as exc:
            logger.warning("Failed to set %s to in_progress: %s", task.id, exc)

        context_str = _build_task_context(plan, completed_outputs, task)

        try:
            flow = TaskExecutionFlow(persistence=_get_task_persistence())
            flow_id = checkpoint.task_flow_ids.get(task.id, flow.flow_id)
            checkpoint.task_flow_ids[task.id] = flow_id
            _save_checkpoint(run_dir, checkpoint)

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
                    output_paths=[str(task_output_dir)] if task_output_dir.exists() else [],
                    validation_notes=flow.state.dialectic_notes,
                    output_summary=flow.state.impl_output[:5000],
                    execution_phases=flow.state.phases_executed,
                )

        except Exception as exc:
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
            phases = " → ".join(result.execution_phases) if result.execution_phases else "dialectic"
            print(f"   {task.id} APPROVED ({result.score}/10) [{phases}]")
            completed_outputs[task.id] = result.output_summary or f"Task completed. Score: {result.score}"
            try:
                update_task_status(
                    path, task.id, "completed",
                    notes=f"Score: {result.score}/10 [{phases}]. {result.validation_notes[:200]}",
                )
            except Exception as exc:
                logger.warning("Failed to update status for completed %s: %s", task.id, exc)
        else:
            phases = " → ".join(result.execution_phases) if result.execution_phases else "dialectic"
            print(f"   {task.id} FAILED ({result.score}/10) [{phases}]")
            failed_task_ids.add(task.id)
            try:
                update_task_status(
                    path, task.id, "failed",
                    notes=f"Score: {result.score}/10 [{phases}]. {result.validation_notes[:200]}",
                )
            except Exception as exc:
                logger.warning("Failed to update status for failed %s: %s", task.id, exc)

        checkpoint.task_results = task_results
        checkpoint.completed_outputs = completed_outputs
        checkpoint.failed_task_ids = sorted(failed_task_ids)
        _save_checkpoint(run_dir, checkpoint)

    # ------------------------------------------------------------------
    # Post-execution: verify completed tasks against PRD acceptance criteria
    # ------------------------------------------------------------------
    plan = load_plan_file(path)  # reload to pick up status changes
    completed_task_ids = [r.task_id for r in task_results if r.success]
    verified_ids: list[str] = []
    failed_verification_ids: list[str] = []

    if completed_task_ids:
        print(f"\n{'='*60}")
        print(f"Post-execution verification against PRD acceptance criteria")
        print(f"Tasks to verify: {len(completed_task_ids)}")
        print(f"{'='*60}")

        prd = _load_prd_for_plan(plan, None)
        acceptance_criteria = _extract_acceptance_criteria(plan, prd)

        for task_id in completed_task_ids:
            task = next((t for t in plan.tasks if t.id == task_id), None)
            if task is None:
                continue
            print(f"\n  Post-verifying {task.id} — {task.title}...")
            try:
                vr = _run_verification(task, acceptance_criteria, vision_context)
                if vr["verified"]:
                    verified_ids.append(task.id)
                    print(f"   {task.id} VERIFIED (score: {vr['score']}/10)")
                    try:
                        update_task_status(
                            path, task.id, "completed",
                            notes=f"[post-verified] score: {vr['score']}/10. {vr['notes'][:200]}",
                        )
                    except Exception as exc:
                        logger.warning("Failed to update post-verified status for %s: %s", task.id, exc)
                else:
                    failed_verification_ids.append(task.id)
                    print(f"   {task.id} VERIFICATION FAILED (score: {vr['score']}/10)")
                    try:
                        update_task_status(
                            path, task.id, "failed",
                            notes=f"[post-verify failed] score: {vr['score']}/10. {vr['notes'][:200]}",
                        )
                    except Exception as exc:
                        logger.warning("Failed to update post-verify-failed status for %s: %s", task.id, exc)
            except Exception as exc:
                failed_verification_ids.append(task_id)
                print(f"   {task_id} verification error: {exc}")

    # ------------------------------------------------------------------
    # Compute and persist user story-level status
    # ------------------------------------------------------------------
    total_tasks = len(plan.tasks)
    already_failed = [r.task_id for r in task_results if not r.success]
    all_failed = already_failed + failed_verification_ids
    total_verified = len(verified_ids)

    if total_verified == total_tasks:
        story_status = "completed"
    elif total_verified > 0:
        story_status = "partially_completed"
    else:
        story_status = "failed"

    try:
        update_user_story_status(path, story_status)
    except Exception as exc:
        logger.warning("Failed to update story status to %s: %s", story_status, exc)

    overall_success = total_verified == total_tasks
    report = ExecutionReport(
        plan_id=plan.user_story_id,
        plan_title=plan.user_story_title,
        run_id=run_id,
        plan_path=str(Path(path).resolve()),
        vision_hash=plan.vision_hash or get_vision_hash(vision_context),
        task_results=task_results,
        overall_success=overall_success,
        verified_tasks=verified_ids,
        failed_verification_tasks=all_failed,
        task_flow_ids=checkpoint.task_flow_ids,
        resumed_from_run_id=resumed_from_run_id,
    )

    report_path = run_dir / "report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)

    safe_id = plan.user_story_id.replace(" ", "_")
    spec_path = run_dir / f"spec_{safe_id}_{run_id}.md"
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(_artifact_markdown(plan))

    print(f"\n{'='*60}")
    print(f"Story {plan.user_story_id}: {story_status}")
    print(f"  Verified: {verified_ids}")
    if all_failed:
        print(f"  Failed:   {all_failed}")
    print(f"{'='*60}")

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
