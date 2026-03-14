"""
Execution of the approved plan: consume UserStoryExecutionPlan and generate artifacts (spec/outline).
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Union

from dialectic.output_paths import resolve_exec_output_dir, resolve_prd_output_dir
from schemas import UserStoryExecutionPlan

from dialectic.prd_flow import OUTPUT_DIR as PRD_OUTPUT_DIR
from dialectic.vision import VisionContext
from execution.plan_loader import find_latest_plan, load_plan

EXEC_OUTPUT_DIR = "exec_output"


def _find_latest_plan() -> Path:
    """Find the most recent execution plan in prd_output/ (exec_*.json)."""
    if PRD_OUTPUT_DIR == "prd_output":
        return find_latest_plan(resolve_prd_output_dir(VisionContext.PROJECT))
    return find_latest_plan(PRD_OUTPUT_DIR)


def _load_plan(plan_path: str) -> UserStoryExecutionPlan:
    return load_plan(plan_path)


def _artifact_markdown(plan: UserStoryExecutionPlan) -> str:
    """Generate Markdown with implementation spec/outline per task (for manual execution or future code generation)."""
    lines = [
        f"# Implementation spec — {plan.user_story_id} {plan.user_story_title}",
        "",
        f"*Generated on {datetime.now().isoformat(timespec='seconds')}*",
        "",
        "---",
        "",
        "## Approach",
        "",
        plan.approach_summary,
        "",
        "---",
        "",
        "## Tasks (execution order)",
        "",
    ]
    for t in sorted(plan.tasks, key=lambda x: (x.order, x.id)):
        deps = f" *Dependencies: {', '.join(t.dependencies)}*" if t.dependencies else ""
        lines.extend([
            f"### {t.id} — {t.title}",
            "",
            t.description,
            deps,
            "",
        ])
    if plan.risks_mitigated:
        lines.extend(["---", "", "## Mitigated risks", ""])
        for r in plan.risks_mitigated:
            lines.append(f"- {r}")
        lines.append("")
    if plan.tech_notes:
        lines.extend(["---", "", "## Technical notes", "", plan.tech_notes, ""])
    return "\n".join(lines).strip() + "\n"


def run_execution(
    plan_path: str | None = None,
    plan: Union[UserStoryExecutionPlan, dict] | None = None,
    output_dir: str | None = None,
) -> dict:
    """
    Consume a UserStoryExecutionPlan and generate an execution artifact (Markdown spec).
    Args:
        plan_path: Path to the plan JSON file (exec_*.json). Ignored if plan is provided.
        plan: Already loaded plan (dict or UserStoryExecutionPlan). Optional.
        output_dir: Output directory (default: exec_output).
    Returns:
        dict with output_path (generated .md file), plan_id, success.
    """
    out_dir = output_dir or str(resolve_exec_output_dir(VisionContext.PROJECT))
    os.makedirs(out_dir, exist_ok=True)

    if plan is not None:
        if isinstance(plan, dict):
            plan_obj = UserStoryExecutionPlan.model_validate(plan)
        else:
            plan_obj = plan
        plan_id = plan_obj.user_story_id
    else:
        path = plan_path
        if path is None or path == "--latest":
            path = str(_find_latest_plan())
        if not os.path.exists(path):
            raise FileNotFoundError(f"Plan not found: {path}")
        plan_obj = _load_plan(path)
        plan_id = plan_obj.user_story_id

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    safe_id = plan_id.replace(" ", "_")
    filename = f"spec_{safe_id}_{timestamp}.md"
    output_path = os.path.join(out_dir, filename)

    content = _artifact_markdown(plan_obj)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "success": True,
        "output_path": output_path,
        "plan_id": plan_id,
        "plan_title": plan_obj.user_story_title,
    }
