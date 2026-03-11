"""
Dialectic flow for planning the execution of a user story.
Produces UserStoryExecutionPlan (thesis → antithesis → synthesis → validation).

Uses native CrewAI features:
- output_pydantic: structured output from Validator (eliminates manual JSON parsing)
- Task guardrails: automatic plan structure validation
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dialectic.agents import (
    _vision_label,
)
from dialectic.export import execution_plan_to_markdown
from dialectic.prd_flow import OUTPUT_DIR
from dialectic.vision import VisionContext, get_vision_hash
from planning.runtime import build_planning_crew
from schemas import PRDSchema, UserStoryExecutionPlan


# ---------------------------------------------------------------------------
# Guardrail: validates plan structure from output_pydantic
# ---------------------------------------------------------------------------

def _plan_guardrail(result) -> tuple[bool, Any]:
    """Ensures validation task returns a valid UserStoryExecutionPlan."""
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, UserStoryExecutionPlan):
        if pydantic_obj.tasks and len(pydantic_obj.tasks) >= 1:
            return (True, result)
        return (False, "Plan must include at least one implementation task (tasks list is empty)")
    return (
        False,
        "Output must be a valid UserStoryExecutionPlan JSON with fields: "
        "user_story_id, user_story_title, approach_summary, tasks, quality_score, "
        "consensus_reached, final_validation_notes. Return ONLY the JSON.",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_latest_prd() -> Path:
    jsons = list(Path(OUTPUT_DIR).glob("PRD_*.json"))
    if not jsons:
        raise FileNotFoundError(f"No PRD found in {OUTPUT_DIR}/")
    return max(jsons, key=lambda p: p.stat().st_mtime)


def _load_prd(path: str) -> tuple[PRDSchema, dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    prd = PRDSchema.model_validate(data)
    return prd, data


def _normalize_us_ref(s: str) -> str:
    s = s.strip().upper()
    if s.isdigit():
        return s
    if s.startswith("US") and len(s) > 2 and s[2:].isdigit():
        return "US" + str(int(s[2:]))
    return s


def _get_user_story(prd: PRDSchema, ref: str | None):
    if ref is None:
        return prd.user_stories[0]
    ref_norm = _normalize_us_ref(ref)
    for us in prd.user_stories:
        if ref_norm == _normalize_us_ref(us.id):
            return us
    try:
        idx = int(ref)
        return prd.user_stories[idx]
    except (ValueError, IndexError):
        raise ValueError(f"User story not found: {ref}. Available: {[u.id for u in prd.user_stories]}")


# ---------------------------------------------------------------------------
# Main planning function
# ---------------------------------------------------------------------------

MIN_PLAN_SCORE = float(os.getenv("MIN_PLAN_SCORE", "7.5"))
MAX_PLAN_RETRIES = int(os.getenv("MAX_PLAN_RETRIES", "3"))


def _ensure_acceptance_checks(plan: UserStoryExecutionPlan, us) -> UserStoryExecutionPlan:
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
        task.acceptance_checks = list(dict.fromkeys(check for check in derived_checks if check))[:4]
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
    except Exception:
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
        prd_path = str(_find_latest_prd())
    prd, _ = _load_prd(prd_path)
    us = _get_user_story(prd, user_story_ref)

    us_context = f"""
User Story: {us.id} — {us.title}
Description: {us.description}
Acceptance criteria: {chr(10).join('- ' + ac for ac in us.acceptance_criteria)}
Effort: {us.effort}
Dependencies: {', '.join(us.dependencies) or 'None'}
"""
    feature_context = f"Feature (PRD): {prd.feature_name}. Objective: {prd.objective}"

    print(f"\n{'='*60}")
    print(f"Dialectic planning — {us.id} {us.title}")
    print(f"{'='*60}\n")

    plan_valid: UserStoryExecutionPlan | None = None

    for attempt in range(MAX_PLAN_RETRIES + 1):
        if attempt > 0:
            print(f"\n--- Planning retry {attempt}/{MAX_PLAN_RETRIES} ---\n")

        result = build_planning_crew(
            feature_context=feature_context,
            us=us,
            us_context=us_context,
            vision_context=vision_context,
            min_plan_score=MIN_PLAN_SCORE,
        ).kickoff()
        plan_valid = _extract_plan(result, us)

        if plan_valid is None:
            print(f"   Failed to extract structured plan (attempt {attempt + 1})")
            continue

        plan_valid = _ensure_acceptance_checks(plan_valid, us)
        plan_valid.source_prd_path = str(Path(prd_path).resolve())
        plan_valid.vision_hash = get_vision_hash(vision_context)

        if plan_valid.quality_score >= MIN_PLAN_SCORE:
            print(f"   Plan approved (score {plan_valid.quality_score}/10)")
            break

        print(f"   Plan score {plan_valid.quality_score}/10 < {MIN_PLAN_SCORE}")

    if plan_valid is None:
        raise RuntimeError(
            f"Planning failed after {MAX_PLAN_RETRIES + 1} attempts: "
            "could not extract a valid UserStoryExecutionPlan from crew output."
        )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{OUTPUT_DIR}/exec_{us.id}_{timestamp}"
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
