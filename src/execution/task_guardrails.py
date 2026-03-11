"""Guardrails for task execution and verification flows."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from dialectic.metrics import emit as emit_metric
from schemas import ValidationOutput, VerificationResult


def _guardrail_success_output(_result, validated_model: BaseModel) -> str:
    """Return a CrewAI-compatible guardrail payload for structured outputs."""
    return validated_model.model_dump_json()


def _quality_guardrail(result) -> tuple[bool, Any]:
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, ValidationOutput):
        if 0.0 <= pydantic_obj.quality_score <= 10.0:
            return True, _guardrail_success_output(result, pydantic_obj)
        emit_metric("guardrail_reject", 1.0, guardrail="quality", reason="score_out_of_range")
        return False, "quality_score must be between 0.0 and 10.0"
    emit_metric("guardrail_reject", 1.0, guardrail="quality", reason="invalid_schema")
    return False, "Output must be valid JSON: quality_score, consensus_reached, final_validation_notes"


def _verification_guardrail(result) -> tuple[bool, Any]:
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, VerificationResult):
        return True, _guardrail_success_output(result, pydantic_obj)
    emit_metric("guardrail_reject", 1.0, guardrail="verification", reason="invalid_schema")
    return False, "Output must be VerificationResult JSON: verified, checks_passed, checks_failed, notes"
