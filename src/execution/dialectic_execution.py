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
import os
from collections import deque
from datetime import datetime
from pathlib import Path

from dialectic.prd_flow import OUTPUT_DIR as PRD_OUTPUT_DIR
from schemas import (
    ImplementationTask,
    UserStoryExecutionPlan,
    TaskExecutionResult,
    ExecutionReport,
)
from execution.runner import _artifact_markdown
from execution.verify import update_task_status
from execution.task_flow import TaskExecutionFlow, TaskFlowState, _task_persistence

EXEC_OUTPUT_DIR = "exec_output"
DEFAULT_MAX_RETRIES_PER_TASK = int(os.getenv("MAX_RETRIES_PER_TASK", "3"))
DEFAULT_MIN_SCORE = float(os.getenv("MIN_QUALITY_SCORE", "7.5"))


# ---------------------------------------------------------------------------
# Plan loading / topological sort
# ---------------------------------------------------------------------------

def _find_latest_plan() -> Path:
    base = Path(PRD_OUTPUT_DIR)
    if not base.exists():
        raise FileNotFoundError(f"Directory {PRD_OUTPUT_DIR} not found.")
    jsons = list(base.glob("exec_*.json"))
    if not jsons:
        raise FileNotFoundError(
            f"No execution plan found in {PRD_OUTPUT_DIR}/ (expected exec_*.json)"
        )
    return max(jsons, key=lambda p: p.stat().st_mtime)


def _load_plan(plan_path: str) -> UserStoryExecutionPlan:
    with open(plan_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return UserStoryExecutionPlan.model_validate(data)


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


# ---------------------------------------------------------------------------
# Main execution orchestrator (uses TaskExecutionFlow per task)
# ---------------------------------------------------------------------------

def run_dialectic_execution(
    plan_path: str | None = None,
    vision_content: str | None = None,
    max_retries_per_task: int = DEFAULT_MAX_RETRIES_PER_TASK,
    output_dir: str | None = None,
) -> dict:
    """
    Execute the plan with native CrewAI Flow per task.

    Each task runs through TaskExecutionFlow:
      dialectic → @router → verify (A+B) → @router → reimplement (C) if needed
    """
    out_dir = Path(output_dir or EXEC_OUTPUT_DIR)
    run_id = datetime.now().strftime("%Y%m%d_%H%M")
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    if vision_content is None:
        vision_path = Path("VISION.md")
        if not vision_path.exists():
            raise FileNotFoundError(
                "VISION.md not found. Provide vision_content or run from the project directory."
            )
        vision_content = vision_path.read_text(encoding="utf-8")

    path = plan_path
    if path is None or path == "--latest":
        path = str(_find_latest_plan())
    if not os.path.exists(path):
        raise FileNotFoundError(f"Plan not found: {path}")

    plan = _load_plan(path)
    ordered_tasks = _topological_sort(plan.tasks)

    print(f"\n{'='*60}")
    print(f"Executing plan — {plan.user_story_id} {plan.user_story_title}")
    print(f"Tasks: {len(ordered_tasks)} | Retries/task: {max_retries_per_task}")
    print(f"Flow: dialectic → verify(A+B) → reimplement(C) if needed")
    print(f"{'='*60}\n")

    task_results: list[TaskExecutionResult] = []
    completed_outputs: dict[str, str] = {}

    for task in ordered_tasks:
        task_output_dir = run_dir / f"{task.id}_output"
        task_output_dir.mkdir(exist_ok=True)
        print(f"\n>>> Executing task {task.id} — {task.title}")

        try:
            update_task_status(path, task.id, "in_progress")
        except Exception:
            pass

        context_str = _build_task_context(plan, completed_outputs, task)

        try:
            flow = TaskExecutionFlow(persistence=_task_persistence)
            flow_result = flow.kickoff(inputs={
                "task_id": task.id,
                "task_title": task.title,
                "task_description": task.description,
                "context_str": context_str,
                "vision_content": vision_content[:6000],
                "acceptance_checks": task.acceptance_checks,
                "min_score": DEFAULT_MIN_SCORE,
                "max_retries": max_retries_per_task,
            })

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

        task_results.append(result)

        if result.success:
            phases = " → ".join(result.execution_phases) if result.execution_phases else "dialectic"
            print(f"   {task.id} APPROVED ({result.score}/10) [{phases}]")
            completed_outputs[task.id] = result.output_summary or f"Task completed. Score: {result.score}"
            try:
                update_task_status(
                    path, task.id, "completed",
                    notes=f"Score: {result.score}/10 [{phases}]. {result.validation_notes[:200]}",
                )
            except Exception:
                pass
        else:
            phases = " → ".join(result.execution_phases) if result.execution_phases else "dialectic"
            print(f"   {task.id} FAILED ({result.score}/10) [{phases}]")
            try:
                update_task_status(
                    path, task.id, "failed",
                    notes=f"Score: {result.score}/10 [{phases}]. {result.validation_notes[:200]}",
                )
            except Exception:
                pass

    overall_success = all(r.success for r in task_results)
    report = ExecutionReport(
        plan_id=plan.user_story_id,
        plan_title=plan.user_story_title,
        run_id=run_id,
        task_results=task_results,
        overall_success=overall_success,
    )

    report_path = run_dir / "report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)

    safe_id = plan.user_story_id.replace(" ", "_")
    spec_path = run_dir / f"spec_{safe_id}_{run_id}.md"
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(_artifact_markdown(plan))

    return {
        "run_id": run_id,
        "output_path": str(run_dir),
        "report_path": str(report_path),
        "plan_id": plan.user_story_id,
        "plan_title": plan.user_story_title,
        "overall_success": overall_success,
        "report": report.model_dump(),
    }
