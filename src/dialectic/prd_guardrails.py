"""Guardrails and retry-feedback helpers for the PRD dialectic flow."""

import json
import logging
from collections.abc import Mapping
from typing import Any, Tuple

from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource

from dialectic.dependency_graph import (
    format_dependency_errors,
    validate_user_story_dependencies,
)
from dialectic.metrics import emit as emit_metric
from schemas import PRDSchema

logger = logging.getLogger(__name__)

RETRY_FEEDBACK_INLINE_CHAR_THRESHOLD = 4000


def _build_retry_feedback_context(
    retry_feedback: str,
    retry_count: int,
) -> tuple[str, list[StringKnowledgeSource]]:
    """Return retry feedback prompt text plus optional knowledge sources."""
    cleaned_feedback = retry_feedback.strip()
    if not cleaned_feedback or retry_count <= 0:
        return "", []

    if len(cleaned_feedback) <= RETRY_FEEDBACK_INLINE_CHAR_THRESHOLD:
        return (
            f"""

PREVIOUS ROUND VALIDATION FEEDBACK:
{cleaned_feedback}

You MUST address every issue listed above in this round.
""",
            [],
        )

    feedback_source = StringKnowledgeSource(
        content=(
            "Previous round validation feedback for the current PRD retry. "
            "Every issue in this feedback must be resolved in the next round.\n\n"
            f"{cleaned_feedback}"
        ),
        chunk_size=1200,
        chunk_overlap=150,
    )
    return (
        """

PREVIOUS ROUND VALIDATION FEEDBACK:
The full validator feedback from the previous round is available in your knowledge sources.
You MUST consult it and address every issue listed there in this round.
""",
        [feedback_source],
    )


def _materialize_plain_data(value: Any) -> Any:
    """Convert flow-state proxy containers into plain Python data recursively."""
    if isinstance(value, Mapping):
        return {str(key): _materialize_plain_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_materialize_plain_data(item) for item in value]
    if isinstance(value, tuple):
        return [_materialize_plain_data(item) for item in value]
    return value


def _extract_prd_from_result(result) -> PRDSchema | None:
    """Extract a PRDSchema from a task result's pydantic or raw JSON output."""
    pydantic_obj = getattr(result, "pydantic", None)
    if isinstance(pydantic_obj, PRDSchema):
        return pydantic_obj

    json_dict = getattr(result, "json_dict", None)
    if isinstance(json_dict, dict):
        try:
            return PRDSchema.model_validate(json_dict)
        except Exception:
            pass

    raw_text = getattr(result, "raw", None)
    if not isinstance(raw_text, str) or not raw_text.strip():
        return None

    try:
        import re

        matches = re.findall(r"```(?:json)?\s*([\s\S]*?)```", raw_text)
        json_str = matches[-1].strip() if matches else raw_text
        start_idx = json_str.find("{")
        if start_idx >= 0:
            json_str = json_str[start_idx:]
        return PRDSchema.model_validate(json.loads(json_str))
    except Exception:
        return None


def _guardrail_success_output(result, validated_model: PRDSchema) -> str:
    """Return a CrewAI-compatible guardrail payload."""
    return validated_model.model_dump_json()


def _prd_guardrail(result) -> Tuple[bool, Any]:
    """Ensure the validation task returns a valid PRDSchema."""
    prd = _extract_prd_from_result(result)
    if prd is not None:
        if prd.user_stories and len(prd.user_stories) >= 1:
            dependency_errors = validate_user_story_dependencies(prd.user_stories)
            if dependency_errors:
                logger.warning(
                    "dependency-graph-rejected by prd guardrail: %s",
                    "; ".join(dependency_errors),
                )
                emit_metric("guardrail_reject", 1.0, guardrail="prd", reason="invalid_dependencies")
                return False, format_dependency_errors(
                    dependency_errors,
                    subject="PRD",
                )
            return True, _guardrail_success_output(result, prd)
        emit_metric("guardrail_reject", 1.0, guardrail="prd", reason="no_user_stories")
        return False, "PRD must include at least one user story"
    emit_metric("guardrail_reject", 1.0, guardrail="prd", reason="invalid_schema")
    return (
        False,
        "Output must be a valid PRDSchema JSON. Include all required fields: "
        "feature_name, objective, macro_impact, user_stories (min 1), "
        "anti_drift_questions (min 5), quality_score, consensus_reached, "
        "final_validation_notes. Use English values for risk_level "
        "(LOW/MEDIUM/HIGH) and effort (XS/S/M/L/XL). Return ONLY the JSON.",
    )
