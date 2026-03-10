"""Tests for guardrail functions across all flow modules."""

import pytest

from dialectic.prd_flow import _prd_guardrail
from execution.task_flow import _quality_guardrail, _verification_guardrail
from schemas import (
    PRDSchema,
    ValidationOutput,
    VerificationResult,
)
from conftest import make_prd


class _FakeResult:
    """Minimal object mimicking CrewAI task result with a .pydantic attribute."""
    def __init__(self, pydantic_obj):
        self.pydantic = pydantic_obj


class TestPrdGuardrail:
    def test_valid_prd(self):
        prd = make_prd()
        ok, result = _prd_guardrail(_FakeResult(prd))
        assert ok is True
        assert isinstance(result, str)

    def test_no_user_stories(self):
        prd = make_prd()
        prd.__dict__["user_stories"] = []
        ok, msg = _prd_guardrail(_FakeResult(prd))
        assert ok is False
        assert "user story" in msg.lower()

    def test_non_pydantic_result(self):
        ok, msg = _prd_guardrail(_FakeResult(None))
        assert ok is False
        assert "PRDSchema" in msg

    def test_wrong_type(self):
        ok, msg = _prd_guardrail(_FakeResult({"not": "a prd"}))
        assert ok is False


class TestQualityGuardrail:
    def test_valid_output(self):
        vo = ValidationOutput(quality_score=8.0, consensus_reached=True, final_validation_notes="good")
        ok, result = _quality_guardrail(_FakeResult(vo))
        assert ok is True
        assert isinstance(result, str)

    def test_score_out_of_range_high(self):
        vo = ValidationOutput.__new__(ValidationOutput)
        object.__setattr__(vo, "quality_score", 15.0)
        object.__setattr__(vo, "consensus_reached", False)
        object.__setattr__(vo, "final_validation_notes", "")
        ok, msg = _quality_guardrail(_FakeResult(vo))
        assert ok is False

    def test_non_pydantic(self):
        ok, msg = _quality_guardrail(_FakeResult(None))
        assert ok is False
        assert "quality_score" in msg.lower()

    def test_boundary_zero(self):
        vo = ValidationOutput(quality_score=0.0)
        ok, _ = _quality_guardrail(_FakeResult(vo))
        assert ok is True

    def test_boundary_ten(self):
        vo = ValidationOutput(quality_score=10.0)
        ok, _ = _quality_guardrail(_FakeResult(vo))
        assert ok is True


class TestVerificationGuardrail:
    def test_valid_result(self):
        vr = VerificationResult(
            verified=True,
            checks_passed=["file exists"],
            checks_failed=[],
            notes="all good",
        )
        ok, result = _verification_guardrail(_FakeResult(vr))
        assert ok is True
        assert isinstance(result, str)

    def test_non_pydantic(self):
        ok, msg = _verification_guardrail(_FakeResult(None))
        assert ok is False
        assert "VerificationResult" in msg

    def test_wrong_type(self):
        ok, msg = _verification_guardrail(_FakeResult("not a result"))
        assert ok is False
