"""
Dialectic flow for planning the execution of a user story.
Produces UserStoryExecutionPlan (thesis → antithesis → synthesis → validation).

Uses native CrewAI features:
- output_pydantic: structured output from Validator (eliminates manual JSON parsing)
- Task guardrails: automatic plan structure validation
- akickoff() + asyncio.wait_for(): native timeout
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from crewai import Task, Crew

from dialectic.agents import visionario, critico_socratico, sintetizador, validador_macro
from dialectic.export import execution_plan_to_markdown
from dialectic.prd_flow import OUTPUT_DIR
from schemas import PRDSchema, UserStoryExecutionPlan

CREW_KICKOFF_TIMEOUT = int(os.getenv("CREW_KICKOFF_TIMEOUT", "300"))


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
# Async crew execution with timeout
# ---------------------------------------------------------------------------

def _run_crew_with_timeout(crew: Crew, timeout: int):
    async def _run():
        return await asyncio.wait_for(crew.akickoff(), timeout=timeout)
    return asyncio.run(_run())


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

def run_user_story_planning(
    prd_path: str | None,
    user_story_ref: str | None,
    vision_content: str,
) -> dict:
    """
    Execute dialectic cycle to generate an implementation plan for a user story.

    Uses native CrewAI features:
    - output_pydantic for structured plan output
    - Task guardrails for output validation
    - akickoff() + asyncio.wait_for() for timeout
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

    task_tese = Task(
        description=f"""
MACRO VISION (VISION.md):
{vision_content}

FEATURE CONTEXT:
{feature_context}

USER STORY TO IMPLEMENT:
{us_context}

Generate the THESIS: an initial implementation plan for this user story.
Include:
1. Summarized technical approach (approach_summary)
2. List of implementation tasks (id, title, description, order, dependencies)
3. Risks you already foresee
4. Relevant technical notes

Be concrete and aligned with the macro vision. Do not invent modules outside the PRD scope.
""",
        expected_output="Structured implementation plan (approach + tasks + risks + notes)",
        agent=visionario,
    )

    task_antitese = Task(
        description=f"""
MACRO VISION:
{vision_content}

The implementation proposal (thesis) for the user story was:
[Visionary's output]

Apply the Socratic method. List ALL:
1. Flaws and weak points of the plan
2. Contradictions with VISION.md or the feature PRD
3. Risks of technical debt or overscope
4. Missing or poorly ordered tasks
5. Acceptance criteria not covered by the plan

Be relentless. Each critique must be specific and actionable.
""",
        expected_output="Detailed critique of the implementation plan",
        agent=critico_socratico,
        context=[task_tese],
    )

    task_sintese = Task(
        description=f"""
MACRO VISION:
{vision_content}

USER STORY: {us.id} — {us.title}

You received:
- The thesis: implementation plan from the Visionary
- The antithesis: critiques from the Socratic Critic

Produce the SYNTHESIS: a refined implementation plan that:
1. Preserves what was good in the thesis
2. Incorporates ALL critiques from the antithesis
3. Lists clear tasks (id, title, description, order, dependencies)
4. Includes approach_summary, risks_mitigated, tech_notes
5. Is aligned with VISION.md and the PRD

Format expected by the Validator: summarized approach, numbered task list, mitigated risks, technical notes.
""",
        expected_output="Refined implementation plan (approach + tasks + mitigated risks + notes)",
        agent=sintetizador,
        context=[task_tese, task_antitese],
    )

    task_validacao = Task(
        description=f"""
Based on the SYNTHESIS of the implementation plan for user story {us.id} — {us.title},
produce the final document.

Fill in:
- user_story_id: "{us.id}"
- user_story_title: "{us.title}"
- approach_summary: summary of the approach (from synthesis)
- tasks: list of ImplementationTask (id, title, description, order, dependencies)
- risks_mitigated: list of risks that were mitigated
- tech_notes: technical notes
- quality_score: float 0-10 (one decimal place). Approve if >= 9.0
- consensus_reached: true if the plan is ready for execution
- final_validation_notes: brief explanation
""",
        expected_output="Valid UserStoryExecutionPlan with quality_score and consensus_reached",
        agent=validador_macro,
        output_pydantic=UserStoryExecutionPlan,
        guardrail=_plan_guardrail,
        guardrail_max_retries=2,
        context=[task_tese, task_antitese, task_sintese],
    )

    crew = Crew(
        agents=[visionario, critico_socratico, sintetizador, validador_macro],
        tasks=[task_tese, task_antitese, task_sintese, task_validacao],
        process="sequential",
        verbose=True,
    )

    print(f"\n{'='*60}")
    print(f"Dialectic planning — {us.id} {us.title}")
    print(f"{'='*60}\n")

    result = _run_crew_with_timeout(crew, CREW_KICKOFF_TIMEOUT)

    # Extract plan via output_pydantic (native CrewAI structured output)
    plan_valid: UserStoryExecutionPlan | None = None
    pydantic_result = getattr(result, "pydantic", None)
    if isinstance(pydantic_result, UserStoryExecutionPlan):
        plan_valid = pydantic_result
    else:
        tasks_out = getattr(result, "tasks_output", None) or []
        if tasks_out:
            last_pydantic = getattr(tasks_out[-1], "pydantic", None)
            if isinstance(last_pydantic, UserStoryExecutionPlan):
                plan_valid = last_pydantic

    # Fallback: if output_pydantic failed, try parsing raw text
    if plan_valid is None:
        raw_text = getattr(result, "raw", None) or str(result)
        tasks_out = getattr(result, "tasks_output", None) or []
        if tasks_out:
            last_raw = getattr(tasks_out[-1], "raw", None)
            if last_raw and isinstance(last_raw, str) and last_raw.strip():
                raw_text = last_raw
        try:
            import re
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw_text)
            json_str = match.group(1).strip() if match else raw_text
            plan_dict = json.loads(json_str)
            plan_dict.setdefault("user_story_id", us.id)
            plan_dict.setdefault("user_story_title", us.title)
            plan_valid = UserStoryExecutionPlan.model_validate(plan_dict)
        except Exception:
            from schemas import ImplementationTask
            plan_valid = UserStoryExecutionPlan(
                user_story_id=us.id,
                user_story_title=us.title,
                approach_summary="Failed to extract structured plan from output.",
                tasks=[ImplementationTask(id="T-001", title="Placeholder", description="N/A", order=1)],
                quality_score=0.0,
                consensus_reached=False,
                final_validation_notes="output_pydantic and manual parsing both failed",
            )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
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
