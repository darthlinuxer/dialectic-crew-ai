"""Task execution context assembly helpers."""

from __future__ import annotations

from schemas import ImplementationTask, UserStoryExecutionPlan


def build_task_context(
    plan: UserStoryExecutionPlan,
    completed_outputs: dict[str, str],
    current_task: ImplementationTask,
) -> str:
    """Render the textual context block for a task execution flow."""
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
        for task_id, output in completed_outputs.items():
            lines.append(f"### {task_id}")
            lines.append(output[:1500] + ("..." if len(output) > 1500 else ""))
            lines.append("")
    lines.extend(
        [
            "## Current task to implement",
            "",
            f"**{current_task.id} — {current_task.title}**",
            "",
            current_task.description,
        ]
    )
    return "\n".join(lines)
