"""Guardrails for task execution and verification flows."""

import logging
import re
from typing import Any, Tuple

from pydantic import BaseModel

from dialectic.metrics import emit as emit_metric
from schemas import ValidationOutput, VerificationResult


logger = logging.getLogger(__name__)


def _guardrail_success_output(_result, validated_model: BaseModel) -> str:
    """Return a CrewAI-compatible guardrail payload for structured outputs."""
    return validated_model.model_dump_json()


_TOOL_CALL_OUTPUT_PATTERN = re.compile(
    r"ChatCompletionMessage(?:Function)?ToolCall\(|function=Function\(arguments=|type='function'",
    re.IGNORECASE,
)


def _looks_like_tool_call_output(raw_text: str) -> bool:
    """Return whether the raw task output appears to be a serialized tool call."""
    stripped = raw_text.strip()
    if not stripped:
        return False
    return bool(_TOOL_CALL_OUTPUT_PATTERN.search(stripped))


def _preview_text(raw_text: str, *, limit: int = 240) -> str:
    """Return a single-line preview suitable for warning logs."""
    collapsed = " ".join(raw_text.split())
    if len(collapsed) <= limit:
        return collapsed
    return f"{collapsed[: limit - 1]}…"


def _text_result_guardrail(result) -> Tuple[bool, Any]:
    """Accept only meaningful plain-text answers, never raw tool-call objects."""
    raw_text = getattr(result, "raw", None)
    if not isinstance(raw_text, str) or not raw_text.strip():
        emit_metric(
            "guardrail_reject",
            1.0,
            guardrail="text_result",
            reason="empty_output",
        )
        return False, "Final answer must be a non-empty plain-text answer."

    if _looks_like_tool_call_output(raw_text):
        preview = _preview_text(raw_text)
        emit_metric(
            "guardrail_reject",
            1.0,
            guardrail="text_result",
            reason="tool_call_output",
        )
        logger.warning(
            "tool-call-output-rejected by text_result guardrail; preview=%r",
            preview,
            extra={
                "event_type": "guardrail_reject",
                "event_name": "tool_call_output_rejected",
                "source_name": "text_result_guardrail",
                "guardrail": "text_result",
                "reason": "tool_call_output",
                "preview": preview,
            },
        )
        return (
            False,
            "Final answer must be a plain-text answer, not a tool call object, "
            "tool arguments, or raw tool output. "
            "If you use tools, execute them first and then return the "
            "completed textual answer only.",
        )

    return True, raw_text.strip()


def _quality_guardrail(result) -> Tuple[bool, Any]:
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, ValidationOutput):
        if 0.0 <= pydantic_obj.quality_score <= 10.0:
            return True, _guardrail_success_output(result, pydantic_obj)
        emit_metric(
            "guardrail_reject",
            1.0,
            guardrail="quality",
            reason="score_out_of_range",
        )
        return False, "quality_score must be between 0.0 and 10.0"
    emit_metric(
        "guardrail_reject",
        1.0,
        guardrail="quality",
        reason="invalid_schema",
    )
    return (
        False,
        "Output must be valid JSON: quality_score, consensus_reached, "
        "final_validation_notes",
    )


def _verification_guardrail(result) -> Tuple[bool, Any]:
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, VerificationResult):
        return True, _guardrail_success_output(result, pydantic_obj)
    emit_metric(
        "guardrail_reject",
        1.0,
        guardrail="verification",
        reason="invalid_schema",
    )
    return (
        False,
        "Output must be VerificationResult JSON: verified, checks_passed, "
        "checks_failed, notes",
    )
