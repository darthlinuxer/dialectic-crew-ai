"""
Dialectic prioritization of improvement opportunities.

Instead of sorting by a static impact label, this module runs a lightweight
3-agent CrewAI debate to rank opportunities by SELF_VISION alignment,
feasibility, and ROI.  Falls back to simple impact sorting when the crew
is unavailable or produces invalid output.

Usage::

    from dialectic.prioritize import dialectic_prioritize

    ranked = dialectic_prioritize(
        opportunities,
        vision_context=VisionContext.SELF,
        max_to_debate=5,
    )
"""

import json
import logging
from typing import Any, Tuple

from pydantic import BaseModel, ValidationError

from dialectic.crewai_runtime import run_crew_kickoff
from dialectic.prioritize_runtime import build_prioritization_crew
from dialectic.vision import VisionContext
from schemas import (
    ImprovementOpportunity,
    PrioritizationResult,
)

logger = logging.getLogger(__name__)

_IMPACT_ORDER = {"high": 0, "medium": 1, "low": 2}


def _build_opportunities_text(opportunities: list[ImprovementOpportunity]) -> str:
    """Serialize opportunities into a readable text block for agent prompts."""
    lines: list[str] = []
    for i, opp in enumerate(opportunities, 1):
        evidence = ", ".join(opp.evidence[:5]) if opp.evidence else "none"
        lines.append(
            f"{i}. [{opp.id}] {opp.title}\n"
            f"   Category: {opp.category}\n"
            f"   Impact estimate: {opp.estimated_impact}\n"
            f"   Description: {opp.description}\n"
            f"   Evidence: {evidence}\n"
        )
    return "\n".join(lines)


def _prioritization_guardrail(result) -> Tuple[bool, Any]:
    """Validate that the Ranker agent produces a valid PrioritizationResult."""
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, PrioritizationResult):
        if pydantic_obj.ranked:
            return (True, _guardrail_success_output(pydantic_obj))
        return (False, "PrioritizationResult must contain at least one ranked item")
    return (
        False,
        "Output must be a valid PrioritizationResult JSON with 'ranked' "
        "(list of PrioritizedOpportunity) and 'debate_summary'.",
    )


def _guardrail_success_output(validated_model: BaseModel) -> str:
    """Serialize structured guardrail output for CrewAI TaskOutput compatibility."""
    return validated_model.model_dump_json()


def _fallback_sort(
    opportunities: list[ImprovementOpportunity],
) -> list[ImprovementOpportunity]:
    """Simple impact-based sort used when the dialectic crew fails."""
    return sorted(
        opportunities,
        key=lambda o: _IMPACT_ORDER.get(o.estimated_impact, 1),
    )


def dialectic_prioritize(
    opportunities: list[ImprovementOpportunity],
    vision_context: VisionContext = VisionContext.SELF,
    max_to_debate: int = 5,
) -> list[ImprovementOpportunity]:
    """Run a 3-agent dialectic debate to rank improvement opportunities.

    Args:
        opportunities: Raw opportunities from introspection (may be empty).
        vision_context: Which vision document to consult.
        max_to_debate: Maximum number of opportunities to send through the
            dialectic debate.  Remaining items are appended in their
            original order after the debated ones.

    Returns:
        Reordered list of ImprovementOpportunity.  On failure, returns
        the input list sorted by impact level (graceful degradation).
    """
    if len(opportunities) <= 1:
        return list(opportunities)

    presorted = _fallback_sort(opportunities)
    debate_candidates = presorted[:max_to_debate]
    remainder = presorted[max_to_debate:]

    opp_text = _build_opportunities_text(debate_candidates)
    opp_ids = [opp.id for opp in debate_candidates]
    opp_ids_str = ", ".join(opp_ids)

    try:
        crew = build_prioritization_crew(
            opp_text=opp_text,
            opp_ids_str=opp_ids_str,
            vision_context=vision_context,
        )
        result = run_crew_kickoff(crew)
    except Exception:
        logger.warning(
            "Dialectic prioritization crew failed; falling back to impact sort",
            exc_info=True,
        )
        return presorted

    prioritization = _extract_prioritization(result)
    if prioritization is None:
        logger.warning(
            "Could not extract PrioritizationResult; falling back to impact sort"
        )
        return presorted

    reordered = _apply_ranking(debate_candidates, prioritization)
    return reordered + remainder


def _extract_prioritization(result: Any) -> PrioritizationResult | None:
    """Extract PrioritizationResult from crew output."""
    pydantic_obj = getattr(result, "pydantic", None)
    if isinstance(pydantic_obj, PrioritizationResult):
        return pydantic_obj

    tasks_out = getattr(result, "tasks_output", None) or []
    if tasks_out:
        last_p = getattr(tasks_out[-1], "pydantic", None)
        if isinstance(last_p, PrioritizationResult):
            return last_p

    raw_text = getattr(result, "raw", None) or ""
    if tasks_out:
        last_raw = getattr(tasks_out[-1], "raw", None)
        if last_raw and isinstance(last_raw, str) and last_raw.strip():
            raw_text = last_raw

    if not raw_text:
        return None

    try:
        import re

        matches = re.findall(r"```(?:json)?\s*([\s\S]*?)```", raw_text)
        json_str = matches[-1].strip() if matches else raw_text
        start_idx = json_str.find("{")
        if start_idx >= 0:
            json_str = json_str[start_idx:]
        data = json.loads(json_str)
        return PrioritizationResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError):
        logger.debug("Failed to parse PrioritizationResult from raw output", exc_info=True)
        return None


def _apply_ranking(
    candidates: list[ImprovementOpportunity],
    prioritization: PrioritizationResult,
) -> list[ImprovementOpportunity]:
    """Reorder candidates based on the dialectic ranking."""
    id_to_opp = {opp.id: opp for opp in candidates}

    ranked_by_score = sorted(
        prioritization.ranked,
        key=lambda p: p.final_priority_score,
        reverse=True,
    )

    reordered: list[ImprovementOpportunity] = []
    seen: set[str] = set()

    for ranked_item in ranked_by_score:
        opp = id_to_opp.get(ranked_item.opportunity_id)
        if opp and ranked_item.opportunity_id not in seen:
            reordered.append(opp)
            seen.add(ranked_item.opportunity_id)

    for opp in candidates:
        if opp.id not in seen:
            reordered.append(opp)
            seen.add(opp.id)

    return reordered
