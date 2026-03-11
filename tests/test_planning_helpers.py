"""Tests for planning helper functions in planning/flow.py."""

import pytest

import planning.flow as planning_flow
from dialectic.vision import VisionContext
from schemas import UserStoryExecutionPlan
from conftest import make_prd, make_task


class TestNormalizeUsRef:
    def test_us_dash_number(self):
        assert planning_flow._normalize_us_ref("US-001") == "US-001"

    def test_us_no_dash(self):
        result = planning_flow._normalize_us_ref("US001")
        assert result == "US1"

    def test_digit_only(self):
        assert planning_flow._normalize_us_ref("1") == "1"

    def test_lowercase(self):
        result = planning_flow._normalize_us_ref("us001")
        assert result == "US1"

    def test_whitespace(self):
        result = planning_flow._normalize_us_ref("  US-001  ")
        assert result == "US-001"

    def test_rejects_non_string(self):
        with pytest.raises(TypeError, match="must be a string"):
            planning_flow._normalize_us_ref(None)


class TestGetUserStory:
    def test_none_returns_first(self):
        prd = make_prd()
        us = planning_flow._get_user_story(prd, None)
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
        us = planning_flow._get_user_story(prd, "US-002")
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
        us = planning_flow._get_user_story(prd, "1")
        assert us.id == "US-002"

    def test_not_found(self):
        prd = make_prd()
        with pytest.raises(ValueError, match="not found"):
            planning_flow._get_user_story(prd, "US-999")


class TestPlanGuardrail:
    def _make_result(self, pydantic_obj):
        class FakeResult:
            def __init__(self, pydantic):
                self.pydantic = pydantic

        return FakeResult(pydantic_obj)

    def test_valid_plan(self):
        plan = UserStoryExecutionPlan(
            user_story_id="US-001",
            user_story_title="Story",
            approach_summary="approach",
            tasks=[make_task()],
            quality_score=9.0,
            final_validation_notes="ok",
        )
        ok, _ = planning_flow._plan_guardrail(self._make_result(plan))
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

        ok, msg = planning_flow._plan_guardrail(FakeResult())
        assert ok is False
        assert "task" in msg.lower()

    def test_non_pydantic(self):
        class FakeResult:
            pydantic = None
        ok, msg = planning_flow._plan_guardrail(FakeResult())
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

        normalized = planning_flow._ensure_acceptance_checks(plan, us)

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

        normalized = planning_flow._ensure_acceptance_checks(plan, us)

        assert normalized.tasks[0].acceptance_checks == ["file exists"]


class TestPlanningRetryFeedback:
    def test_retry_propagates_previous_validation_notes(self, tmp_path, monkeypatch):
        prd = make_prd()
        prd_path = tmp_path / "prd.json"
        prd_path.write_text(prd.model_dump_json(indent=2), encoding="utf-8")
        monkeypatch.setattr(planning_flow, "OUTPUT_DIR", str(tmp_path))
        monkeypatch.setattr(planning_flow, "MIN_PLAN_SCORE", 7.5)
        monkeypatch.setattr(planning_flow, "MAX_PLAN_RETRIES", 1)

        captured_retry_blocks: list[str] = []

        plans = [
            UserStoryExecutionPlan(
                user_story_id="US-001",
                user_story_title="Story",
                approach_summary="First pass",
                tasks=[make_task()],
                quality_score=6.5,
                final_validation_notes="Cover the missing acceptance criteria.",
            ),
            UserStoryExecutionPlan(
                user_story_id="US-001",
                user_story_title="Story",
                approach_summary="Second pass",
                tasks=[make_task()],
                quality_score=8.5,
                final_validation_notes="Looks good.",
            ),
        ]

        class FakeCrew:
            def __init__(self, plan):
                self._plan = plan

            def kickoff(self):
                return type("CrewResult", (), {"pydantic": self._plan})()

        def fake_build_planning_crew(**kwargs):
            captured_retry_blocks.append(kwargs["retry_feedback_block"])
            return FakeCrew(plans[len(captured_retry_blocks) - 1])

        monkeypatch.setattr(planning_flow, "build_planning_crew", fake_build_planning_crew)

        result = planning_flow.run_user_story_planning(
            prd_path=str(prd_path),
            user_story_ref=None,
            vision_context=VisionContext.PROJECT,
        )

        assert result["quality_score"] == 8.5
        assert captured_retry_blocks[0] == ""
        assert "Cover the missing acceptance criteria." in captured_retry_blocks[1]
