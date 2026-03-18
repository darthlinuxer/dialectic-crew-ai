"""
Dialectic flow for planning the execution of a user story.
Produces UserStoryExecutionPlan (thesis → antithesis → synthesis → validation).

Uses native CrewAI features:
- output_pydantic: structured output from Validator (eliminates manual JSON parsing)
- Task guardrails: automatic plan structure validation
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Tuple

from pydantic import BaseModel, ValidationError

from dialectic.crewai_runtime import run_crew_kickoff
from dialectic.dependency_graph import (
    format_dependency_errors,
    validate_task_dependencies,
)
from dialectic.export import execution_plan_to_markdown
from dialectic.output_paths import resolve_prd_output_dir
from dialectic.prd_guardrails import _build_retry_feedback_context
from dialectic.prd_flow import OUTPUT_DIR
from dialectic.target import resolve_active_project_root, temporary_working_directory
from dialectic.vision import VisionContext, get_vision_hash
from planning.runtime import build_planning_crew
from schemas import PRDSchema, UserStory, UserStoryExecutionPlan


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Guardrail: validates plan structure from output_pydantic
# ---------------------------------------------------------------------------


def _plan_guardrail(result) -> Tuple[bool, Any]:
    """Ensures validation task returns a valid UserStoryExecutionPlan."""
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, UserStoryExecutionPlan):
        if pydantic_obj.tasks and len(pydantic_obj.tasks) >= 1:
            dependency_errors = validate_task_dependencies(pydantic_obj.tasks)
            if dependency_errors:
                logger.warning(
                    "dependency-graph-rejected by plan guardrail: %s",
                    "; ".join(dependency_errors),
                )
                return (
                    False,
                    format_dependency_errors(
                        dependency_errors,
                        subject="Plan",
                    ),
                )
            return (True, _guardrail_success_output(pydantic_obj))
        return (
            False,
            "Plan must include at least one implementation task (tasks list is empty)",
        )
    return (
        False,
        "Output must be a valid UserStoryExecutionPlan JSON with fields: "
        "user_story_id, user_story_title, approach_summary, tasks, quality_score, "
        "consensus_reached, final_validation_notes. Return ONLY the JSON.",
    )


def _guardrail_success_output(validated_model: BaseModel) -> str:
    """Serialize structured guardrail output for CrewAI TaskOutput compatibility."""
    return validated_model.model_dump_json()


class _PlanningPRDMetadata(BaseModel):
    """Minimal PRD metadata needed by the planning flow."""

    feature_name: str
    objective: str
    user_stories: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolved_output_dir(vision_context: VisionContext) -> Path:
    if OUTPUT_DIR != "prd_output":
        return Path(OUTPUT_DIR)
    return resolve_prd_output_dir(vision_context)


def _find_latest_prd(vision_context: VisionContext = VisionContext.PROJECT) -> Path:
    candidates: list[Path] = []
    for path in _resolved_output_dir(vision_context).glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if _is_prd_payload(data):
            candidates.append(path)
    if not candidates:
        raise FileNotFoundError(
            f"No PRD found in {_resolved_output_dir(vision_context)}/"
        )
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _is_prd_payload(data: Any) -> bool:
    return (
        isinstance(data, dict)
        and isinstance(data.get("feature_name"), str)
        and isinstance(data.get("objective"), str)
        and isinstance(data.get("user_stories"), list)
    )


def _load_prd(path: str) -> tuple[_PlanningPRDMetadata, dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    prd = _PlanningPRDMetadata.model_validate(data)
    return prd, data


def _normalize_us_ref(s: str) -> str:
    if not isinstance(s, str):
        raise TypeError("user story reference must be a string")
    s = s.strip().upper()
    if s.isdigit():
        return s
    if s.startswith("US") and len(s) > 2 and s[2:].isdigit():
        return "US" + str(int(s[2:]))
    return s


def _get_user_story(
    prd: PRDSchema | _PlanningPRDMetadata, ref: str | None
) -> UserStory:
    raw_stories: list[UserStory | dict[str, Any]] = list(prd.user_stories)
    if not raw_stories:
        raise ValueError("PRD does not contain any user stories")

    if ref is None:
        return _validate_user_story(raw_stories[0], index=0)
    ref_norm = _normalize_us_ref(ref)
    for index, us in enumerate(raw_stories):
        us_id = us.id if isinstance(us, UserStory) else us.get("id")
        if isinstance(us_id, str) and ref_norm == _normalize_us_ref(us_id):
            return _validate_user_story(us, index=index)
    try:
        idx = int(ref)
        return _validate_user_story(raw_stories[idx], index=idx)
    except (ValueError, IndexError) as exc:
        available = [
            us.id if isinstance(us, UserStory) else us.get("id", f"index:{index}")
            for index, us in enumerate(raw_stories)
        ]
        raise ValueError(
            f"User story not found: {ref}. Available: {available}"
        ) from exc


def _validate_user_story(
    user_story: UserStory | dict[str, Any], *, index: int
) -> UserStory:
    if isinstance(user_story, UserStory):
        return user_story
    try:
        return UserStory.model_validate(user_story)
    except ValidationError as exc:
        story_id = user_story.get("id", f"index {index}")
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise ValueError(f"User story {story_id} is invalid in PRD: {details}") from exc


# ---------------------------------------------------------------------------
# Main planning function
# ---------------------------------------------------------------------------

MIN_PLAN_SCORE = float(os.getenv("MIN_PLAN_SCORE", "7.5"))
MAX_PLAN_RETRIES = int(os.getenv("MAX_PLAN_RETRIES", "3"))


def _ensure_acceptance_checks(
    plan: UserStoryExecutionPlan, us
) -> UserStoryExecutionPlan:
    fallback_criteria = [
        f"Contributes to acceptance criterion: {criterion}"
        for criterion in us.acceptance_criteria[:3]
    ]
    for task in plan.tasks:
        if task.acceptance_checks:
            continue
        derived_checks = [
            f"Implementation for {task.id} exists and satisfies: {task.title}",
            f"Task outcome matches description: {task.description}",
            *fallback_criteria,
        ]
        task.acceptance_checks = list(
            dict.fromkeys(check for check in derived_checks if check)
        )[:4]
    return plan


def _extract_plan(result, us) -> UserStoryExecutionPlan | None:
    """Extract UserStoryExecutionPlan from crew result via pydantic or raw text fallback."""
    pydantic_result = getattr(result, "pydantic", None)
    if isinstance(pydantic_result, UserStoryExecutionPlan):
        return pydantic_result

    tasks_out = getattr(result, "tasks_output", None) or []
    if tasks_out:
        last_pydantic = getattr(tasks_out[-1], "pydantic", None)
        if isinstance(last_pydantic, UserStoryExecutionPlan):
            return last_pydantic

    raw_text = getattr(result, "raw", None) or str(result)
    if tasks_out:
        last_raw = getattr(tasks_out[-1], "raw", None)
        if last_raw and isinstance(last_raw, str) and last_raw.strip():
            raw_text = last_raw
    try:
        import re

        matches = re.findall(r"```(?:json)?\s*([\s\S]*?)```", raw_text)
        json_str = matches[-1].strip() if matches else raw_text
        start_idx = json_str.find("{")
        if start_idx >= 0:
            json_str = json_str[start_idx:]
        plan_dict = json.loads(json_str)
        plan_dict.setdefault("user_story_id", us.id)
        plan_dict.setdefault("user_story_title", us.title)
        return UserStoryExecutionPlan.model_validate(plan_dict)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError):
        return None


def run_user_story_planning(
    prd_path: str | None,
    user_story_ref: str | None,
    vision_context: VisionContext = VisionContext.PROJECT,
) -> dict:
    """
    Execute dialectic cycle to generate an implementation plan for a user story.
    Retries up to MAX_PLAN_RETRIES times if quality_score < MIN_PLAN_SCORE.

    Uses native CrewAI features:
    - output_pydantic for structured plan output
    - Task guardrails for output validation
    """
    if prd_path is None:
        prd_path = str(_find_latest_prd(vision_context))
    prd, data = _load_prd(prd_path)
    us = _get_user_story(prd, user_story_ref)

    us_context = f"""
User Story: {us.id} — {us.title}
Description: {us.description}
Acceptance criteria: {chr(10).join("- " + ac for ac in us.acceptance_criteria)}
Effort: {us.effort}
Dependencies: {", ".join(us.dependencies) or "None"}
"""
    feature_context = f"Feature (PRD): {prd.feature_name}. Objective: {prd.objective}"

    print(f"\n{'=' * 60}")
    print(f"Dialectic planning — {us.id} {us.title}")
    print(f"{'=' * 60}\n")

    plan_valid: UserStoryExecutionPlan | None = None
    retry_feedback = ""

    for attempt in range(MAX_PLAN_RETRIES + 1):
        if attempt > 0:
            print(f"\n--- Planning retry {attempt}/{MAX_PLAN_RETRIES} ---\n")

        retry_feedback_block, retry_feedback_sources = _build_retry_feedback_context(
            retry_feedback,
            attempt,
        )

        with temporary_working_directory(resolve_active_project_root()):
            crew = build_planning_crew(
                feature_context=feature_context,
                us=us,
                us_context=us_context,
                vision_context=vision_context,
                min_plan_score=MIN_PLAN_SCORE,
                retry_feedback_block=retry_feedback_block,
                retry_feedback_sources=retry_feedback_sources,
            )
            result = run_crew_kickoff(crew)
        plan_valid = _extract_plan(result, us)

        if plan_valid is None:
            print(f"   Failed to extract structured plan (attempt {attempt + 1})")
            retry_feedback = "The previous planning round failed to produce a valid structured execution plan."
            continue

        plan_valid = _ensure_acceptance_checks(plan_valid, us)
        plan_valid.source_prd_path = str(Path(prd_path).resolve())
        plan_valid.vision_hash = get_vision_hash(vision_context)
        plan_valid.source_roadmap_path = data.get("source_roadmap_path") or None
        plan_valid.source_roadmap_label = data.get("source_roadmap_label") or None
        plan_valid.source_roadmap_key = data.get("source_roadmap_key") or None

        if plan_valid.quality_score >= MIN_PLAN_SCORE:
            print(f"   Plan approved (score {plan_valid.quality_score}/10)")
            break

        print(f"   Plan score {plan_valid.quality_score}/10 < {MIN_PLAN_SCORE}")
        retry_feedback = plan_valid.final_validation_notes.strip()

    if plan_valid is None:
        raise RuntimeError(
            f"Planning failed after {MAX_PLAN_RETRIES + 1} attempts: "
            "could not extract a valid UserStoryExecutionPlan from crew output."
        )

    output_dir = _resolved_output_dir(vision_context)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = str(output_dir / f"exec_{us.id}_{timestamp}")
    with open(f"{base}.json", "w", encoding="utf-8") as f:
        json.dump(plan_valid.model_dump(), f, indent=2, ensure_ascii=False)
    with open(f"{base}.md", "w", encoding="utf-8") as f:
        f.write(execution_plan_to_markdown(plan_valid))
    print(f"\nPlan saved: {base}.json and {base}.md")
    return {
        "plan": plan_valid.model_dump(),
        "quality_score": plan_valid.quality_score,
        "plan_path_json": f"{base}.json",
        "plan_path_md": f"{base}.md",
    }
