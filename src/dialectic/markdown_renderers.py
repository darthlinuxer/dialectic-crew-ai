from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import List, Union

from dialectic.config import ExportConfig
from dialectic.vision import VisionContext, get_vision_hash
from schemas import PRDSchema, UserStoryExecutionPlan

logger = logging.getLogger(__name__)


def execution_plan_to_markdown(plan: Union[UserStoryExecutionPlan, dict]) -> str:
    """Convert an execution plan to Markdown."""
    if isinstance(plan, dict):
        try:
            plan = UserStoryExecutionPlan.model_validate(plan)
        except Exception as exc:
            raise ValueError("Invalid execution plan data for markdown export") from exc
    lines = [
        f"# Execution Plan — {plan.user_story_id} {plan.user_story_title}",
        "",
        f"**Score:** {plan.quality_score}/10.0  |  **Consensus:** {'Yes' if plan.consensus_reached else 'No'}",
        "",
        "---",
        "",
        "## Approach",
        "",
        plan.approach_summary,
        "",
        "---",
        "",
        "## Tasks",
        "",
    ]
    for task in sorted(plan.tasks, key=lambda item: (item.order, item.id)):
        lines.append(f"### {task.id} — {task.title}")
        lines.append("")
        lines.append(task.description)
        if task.dependencies:
            lines.append("")
            lines.append(f"*Dependencies:* {', '.join(task.dependencies)}")
        lines.append("")
    if plan.risks_mitigated:
        lines.extend(["---", "", "## Mitigated Risks", ""])
        for risk in plan.risks_mitigated:
            lines.append(f"- {risk}")
        lines.append("")
    if plan.tech_notes:
        lines.extend(["---", "", "## Technical Notes", "", plan.tech_notes, ""])
    lines.extend(
        ["---", "", "## Validation", "", plan.final_validation_notes.strip(), ""]
    )
    return "\n".join(lines).strip() + "\n"


def prd_to_markdown(prd: Union[PRDSchema, dict]) -> str:
    """Convert a PRD to a narrative Markdown document."""
    if isinstance(prd, dict):
        prd = PRDSchema.model_validate(prd)

    lines = [
        f"# PRD — {prd.feature_name}",
        "",
        f"**Version:** {prd.version}  |  **Score:** {prd.quality_score}/10.0  |  **Consensus:** {'Yes' if prd.consensus_reached else 'No'}",
        "",
        "---",
        "",
        "## Objective",
        "",
        prd.objective,
        "",
        "---",
        "",
        "## Macro Impact",
        "",
        f"- **Modules affected:** {', '.join(prd.macro_impact.modules_affected)}",
        f"- **Risk level:** {prd.macro_impact.risk_level}",
        f"- **Performance impact:** {prd.macro_impact.performance_impact}",
        f"- **Security impact:** {prd.macro_impact.security_impact}",
        "",
        "---",
        "",
        "## User Stories",
        "",
    ]

    for user_story in prd.user_stories:
        lines.extend(
            [
                f"### {user_story.id} — {user_story.title}",
                "",
                user_story.description,
                "",
                "**Acceptance criteria:**",
                "",
            ]
        )
        for criterion in user_story.acceptance_criteria:
            lines.append(f"- {criterion}")
        lines.extend(
            [
                "",
                f"**Effort:** {user_story.effort}",
                "",
            ]
        )
        if user_story.dependencies:
            lines.append(f"**Dependencies:** {', '.join(user_story.dependencies)}")
            lines.append("")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## Anti-Drift Questions",
            "",
        ]
    )
    for question in prd.anti_drift_questions:
        lines.append(f"- **{question.question}** — {question.answer}")
    lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## Final Validation",
            "",
            prd.final_validation_notes.strip(),
            "",
        ]
    )

    return "\n".join(lines).strip() + "\n"


def render_markdown(
    prd: PRDSchema,
    config: ExportConfig,
    vision_context: VisionContext = VisionContext.PROJECT,
) -> str:
    """Render final Markdown with metadata frontmatter and schema-derived body."""
    vision_hash = get_vision_hash(vision_context)
    if vision_hash is None:
        logger.debug(
            "Could not read vision document to compute hash; continuing without vision_hash."
        )

    quality = getattr(prd, "quality_score", None)
    validation_status = getattr(prd, "validation_status", None)
    if validation_status is None:
        validation_status = (
            "approved" if getattr(prd, "consensus_reached", False) else "unapproved"
        )

    generated_at = datetime.now(tz=timezone.utc).isoformat()

    front: List[str] = ["---"]
    if quality is not None:
        front.append(f"quality_score: {quality}")
    if validation_status is not None:
        front.append(f"validation_status: {validation_status}")
    if generated_at:
        front.append(f"generated_at: {generated_at}")
    if vision_hash:
        front.append(f"vision_hash: {vision_hash}")
    front.extend(["---", ""])

    if isinstance(prd, dict):
        prd = PRDSchema.model_validate(prd)

    body_lines: List[str] = []
    body_lines.append("# Objective")
    body_lines.append("")
    body_lines.append(prd.objective)
    body_lines.append("")

    body_lines.append("## Macro Impact")
    body_lines.append("")
    macro_impact = prd.macro_impact
    body_lines.append(f"- Modules affected: {', '.join(macro_impact.modules_affected)}")
    body_lines.append(f"- Risk level: {macro_impact.risk_level}")
    body_lines.append(f"- Performance impact: {macro_impact.performance_impact}")
    body_lines.append(f"- Security impact: {macro_impact.security_impact}")
    body_lines.append("")

    body_lines.append("## User Stories")
    body_lines.append("")
    for user_story in prd.user_stories:
        body_lines.append(f"### {user_story.id} — {user_story.title}")
        body_lines.append("")
        body_lines.append(user_story.description)
        body_lines.append("")
        body_lines.append("**Acceptance criteria:**")
        body_lines.append("")
        for criterion in user_story.acceptance_criteria:
            body_lines.append(f"- {criterion}")
        body_lines.append("")
        body_lines.append(f"**Effort:** {user_story.effort}")
        body_lines.append("")
        if getattr(user_story, "dependencies", None):
            body_lines.append(f"**Dependencies:** {', '.join(user_story.dependencies)}")
            body_lines.append("")

    body_lines.append("## Anti-Drift Questions")
    body_lines.append("")
    for question in prd.anti_drift_questions:
        body_lines.append(f"- **{question.question}** — {question.answer}")
    body_lines.append("")

    if getattr(prd, "vision_hash", None):
        body_lines.append("## Runtime Provenance")
        body_lines.append("")
        body_lines.append(f"- vision_hash: {prd.vision_hash}")
        source_prd_path = getattr(prd, "source_prd_path", None)
        if source_prd_path:
            body_lines.append(f"- source_prd_path: {source_prd_path}")
        body_lines.append("")

    _ = config
    return "\n".join(front + body_lines)
