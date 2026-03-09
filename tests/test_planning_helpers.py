"""Tests for planning helper functions in planning/flow.py."""

import pytest

from planning.flow import (
    _normalize_us_ref,
    _get_user_story,
    _plan_guardrail,
    _ensure_acceptance_checks,
)
from schemas import UserStoryExecutionPlan
from conftest import make_prd, make_task


class TestNormalizeUsRef:
    def test_us_dash_number(self):
        assert _normalize_us_ref("US-001") == "US-001"

    def test_us_no_dash(self):
        result = _normalize_us_ref("US001")
        assert result == "US1"

    def test_digit_only(self):
        assert _normalize_us_ref("1") == "1"

    def test_lowercase(self):
        result = _normalize_us_ref("us001")
        assert result == "US1"

    def test_whitespace(self):
        result = _normalize_us_ref("  US-001  ")
        assert result == "US-001"


class TestGetUserStory:
    def test_none_returns_first(self):
        prd = make_prd()
        us = _get_user_story(prd, None)
        assert us.id == "US-001"

    def test_by_id(self):
        from schemas import UserStory
        prd = make_prd(
            user_stories=[
                UserStory(id="US-001", title="A", description="...",
                         acceptance_criteria=["a", "b", "c"], effort="S"),
                UserStory(id="US-002", title="B", description="...",
                         acceptance_criteria=["a", "b", "c"], effort="M"),
            ]
        )
        us = _get_user_story(prd, "US-002")
        assert us.id == "US-002"

    def test_by_index(self):
        from schemas import UserStory
        prd = make_prd(
            user_stories=[
                UserStory(id="US-001", title="A", description="...",
                         acceptance_criteria=["a", "b", "c"], effort="S"),
                UserStory(id="US-002", title="B", description="...",
                         acceptance_criteria=["a", "b", "c"], effort="M"),
            ]
        )
        us = _get_user_story(prd, "1")
        assert us.id == "US-002"

    def test_not_found(self):
        prd = make_prd()
        with pytest.raises(ValueError, match="not found"):
            _get_user_story(prd, "US-999")


class TestPlanGuardrail:
    def _make_result(self, pydantic_obj):
        class FakeResult:
            pass
        r = FakeResult()
        r.pydantic = pydantic_obj
        return r

    def test_valid_plan(self):
        plan = UserStoryExecutionPlan(
            user_story_id="US-001",
            user_story_title="Story",
            approach_summary="approach",
            tasks=[make_task()],
            quality_score=9.0,
            final_validation_notes="ok",
        )
        ok, result = _plan_guardrail(self._make_result(plan))
        assert ok is True

    def test_empty_tasks(self):
        plan = UserStoryExecutionPlan.__new__(UserStoryExecutionPlan)
        object.__setattr__(plan, "__dict__", {
            "user_story_id": "US-001",
            "user_story_title": "Story",
            "approach_summary": "approach",
            "tasks": [],
            "quality_score": 9.0,
            "final_validation_notes": "ok",
        })

        class FakeResult:
            pydantic = plan

        ok, msg = _plan_guardrail(FakeResult())
        assert ok is False
        assert "task" in msg.lower()

    def test_non_pydantic(self):
        class FakeResult:
            pydantic = None
        ok, msg = _plan_guardrail(FakeResult())
        assert ok is False
        assert "UserStoryExecutionPlan" in msg


class TestEnsureAcceptanceChecks:
    def test_adds_fallback_checks_when_missing(self):
        prd = make_prd()
        us = prd.user_stories[0]
        plan = UserStoryExecutionPlan(
            user_story_id=us.id,
            user_story_title=us.title,
            approach_summary="approach",
            tasks=[make_task(acceptance_checks=[])],
            quality_score=9.0,
            final_validation_notes="ok",
        )

        normalized = _ensure_acceptance_checks(plan, us)

        assert normalized.tasks[0].acceptance_checks
        assert any("Contributes to acceptance criterion" in item for item in normalized.tasks[0].acceptance_checks)

    def test_preserves_existing_checks(self):
        prd = make_prd()
        us = prd.user_stories[0]
        plan = UserStoryExecutionPlan(
            user_story_id=us.id,
            user_story_title=us.title,
            approach_summary="approach",
            tasks=[make_task(acceptance_checks=["file exists"])],
            quality_score=9.0,
            final_validation_notes="ok",
        )

        normalized = _ensure_acceptance_checks(plan, us)

        assert normalized.tasks[0].acceptance_checks == ["file exists"]
