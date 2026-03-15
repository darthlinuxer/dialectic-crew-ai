# pyright: reportPrivateUsage=none

import json
import logging
from typing import Any, cast

import pytest

import planning.flow as planning_flow
from dialectic.vision import VisionContext
from schemas import UserStory, UserStoryExecutionPlan
from tests.conftest import make_prd, make_task


normalize_us_ref = cast(Any, planning_flow.__dict__["_normalize_us_ref"])
get_user_story = cast(Any, planning_flow.__dict__["_get_user_story"])
planning_prd_metadata = cast(Any, planning_flow.__dict__["_PlanningPRDMetadata"])
plan_guardrail = cast(Any, planning_flow.__dict__["_plan_guardrail"])
ensure_acceptance_checks = cast(Any, planning_flow.__dict__["_ensure_acceptance_checks"])
find_latest_prd = cast(Any, planning_flow.__dict__["_find_latest_prd"])
find_agentic_instruction_issues = cast(
    Any,
    planning_flow.__dict__["_find_agentic_instruction_issues"],
)


class TestNormalizeUsRef:
    def test_us_dash_number(self):
        assert normalize_us_ref("US-001") == "US-001"

    def test_us_no_dash(self):
        result = normalize_us_ref("US001")
        assert result == "US1"

    def test_digit_only(self):
        assert normalize_us_ref("1") == "1"

    def test_lowercase(self):
        result = normalize_us_ref("us001")
        assert result == "US1"

    def test_whitespace(self):
        result = normalize_us_ref("  US-001  ")
        assert result == "US-001"

    def test_rejects_non_string(self):
        with pytest.raises(TypeError, match="must be a string"):
            normalize_us_ref(None)


class TestGetUserStory:
    def test_none_returns_first(self):
        prd = make_prd()
        us = get_user_story(prd, None)
        assert us.id == "US-001"

    def test_by_id(self):
        prd = make_prd(
            user_stories=[
                UserStory(id="US-001", title="A", description="...",
                         acceptance_criteria=["a", "b", "c"], effort="S"),
                UserStory(id="US-002", title="B", description="...",
                         acceptance_criteria=["a", "b", "c"], effort="M"),
            ]
        )
        us = get_user_story(prd, "US-002")
        assert us.id == "US-002"

    def test_by_index(self):
        prd = make_prd(
            user_stories=[
                UserStory(id="US-001", title="A", description="...",
                         acceptance_criteria=["a", "b", "c"], effort="S"),
                UserStory(id="US-002", title="B", description="...",
                         acceptance_criteria=["a", "b", "c"], effort="M"),
            ]
        )
        us = get_user_story(prd, "1")
        assert us.id == "US-002"

    def test_not_found(self):
        prd = make_prd()
        with pytest.raises(ValueError, match="not found"):
            get_user_story(prd, "US-999")

    def test_selected_valid_story_ignores_invalid_unrelated_story(self):
        prd = planning_prd_metadata.model_validate(
            {
                "feature_name": "Memory Fabric",
                "objective": "Plan a valid story only",
                "user_stories": [
                    UserStory(
                        id="US-001",
                        title="Valid story",
                        description="Works fine",
                        acceptance_criteria=["A", "B", "C"],
                        effort="M",
                        dependencies=[],
                    ).model_dump(),
                    {
                        "id": "US-999",
                        "title": "Broken story",
                        "description": "Legacy malformed data",
                        "acceptance_criteria": ["A", "effort ", ""],
                        "effort": "M",
                        "dependencies": [],
                    },
                ],
            }
        )

        us = get_user_story(prd, "US-001")

        assert us.id == "US-001"

    def test_selected_invalid_story_raises_clear_error(self):
        prd = planning_prd_metadata.model_validate(
            {
                "feature_name": "Memory Fabric",
                "objective": "Catch malformed requested story",
                "user_stories": [
                    {
                        "id": "US-008",
                        "title": "Broken story",
                        "description": "Legacy malformed data",
                        "acceptance_criteria": ["Golden dataset owner defined.", "effort "],
                        "effort": "M",
                        "dependencies": [],
                    }
                ],
            }
        )

        with pytest.raises(ValueError, match="US-008 is invalid"):
            get_user_story(prd, "US-008")


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
        ok, payload = plan_guardrail(self._make_result(plan))
        assert ok is True
        assert isinstance(payload, str)
        assert '"user_story_id":"US-001"' in payload
        assert '"quality_score":9.0' in payload

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

        ok, msg = plan_guardrail(FakeResult())
        assert ok is False
        assert "task" in msg.lower()

    def test_non_pydantic(self):
        class FakeResult:
            pydantic = None
        ok, msg = plan_guardrail(FakeResult())
        assert ok is False
        assert "UserStoryExecutionPlan" in msg

    def test_rejects_circular_task_dependencies(self):
        plan = UserStoryExecutionPlan(
            user_story_id="US-001",
            user_story_title="Story",
            approach_summary="approach",
            tasks=[
                make_task(id="T-001", dependencies=["T-002"]),
                make_task(id="T-002", order=2, dependencies=["T-001"]),
            ],
            quality_score=9.0,
            final_validation_notes="ok",
        )

        ok, payload = plan_guardrail(self._make_result(plan))

        assert ok is False
        assert "circular dependenc" in payload.lower()

    def test_rejects_unknown_task_dependencies(self):
        plan = UserStoryExecutionPlan(
            user_story_id="US-001",
            user_story_title="Story",
            approach_summary="approach",
            tasks=[make_task(id="T-001", dependencies=["T-999"])],
            quality_score=9.0,
            final_validation_notes="ok",
        )

        ok, payload = plan_guardrail(self._make_result(plan))

        assert ok is False
        assert "unknown dependenc" in payload.lower()

    def test_logs_dependency_rejection(self, caplog):
        plan = UserStoryExecutionPlan(
            user_story_id="US-001",
            user_story_title="Story",
            approach_summary="approach",
            tasks=[make_task(id="T-001", dependencies=["T-999"])],
            quality_score=9.0,
            final_validation_notes="ok",
        )

        with caplog.at_level(logging.WARNING):
            ok, _ = plan_guardrail(self._make_result(plan))

        assert ok is False
        assert "dependency-graph-rejected by plan guardrail" in caplog.text

    def test_rejects_task_descriptions_with_agent_tool_workflow_text(self):
        plan = UserStoryExecutionPlan(
            user_story_id="US-001",
            user_story_title="Story",
            approach_summary="approach",
            tasks=[
                make_task(
                    description=(
                        "Bootstrap context, run list_directory {\"directory\":\"./\"}, "
                        "then write_to_file and output implementation summary in agent response."
                    )
                )
            ],
            quality_score=9.0,
            final_validation_notes="ok",
        )

        ok, payload = plan_guardrail(self._make_result(plan))

        assert ok is False
        assert "implementation deliverables" in payload.lower()
        assert "T-001 description contains agent/tool workflow text" in payload


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

        normalized = ensure_acceptance_checks(plan, us)

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

        normalized = ensure_acceptance_checks(plan, us)

        assert normalized.tasks[0].acceptance_checks == ["file exists"]


class TestAgenticInstructionFiltering:
    def test_finds_tool_workflow_in_task_fields(self):
        plan = UserStoryExecutionPlan(
            user_story_id="US-001",
            user_story_title="Story",
            approach_summary="approach",
            tasks=[
                make_task(
                    id="T-007",
                    description="Use write_to_file to create the schema and ask Which would be most useful next?",
                )
            ],
            quality_score=8.5,
            final_validation_notes="ok",
        )

        issues = find_agentic_instruction_issues(plan)

        assert issues
        assert "T-007" in issues[0]
        assert "write_to_file" in issues[0]


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


class TestLatestPrdLoading:
    def test_find_latest_prd_accepts_slugged_exports(self, tmp_path, monkeypatch):
        monkeypatch.setattr(planning_flow, "OUTPUT_DIR", str(tmp_path))
        older = tmp_path / "PRD_20260313_090000.json"
        older.write_text(
            json.dumps(make_prd(feature_name="Older Feature").model_dump()),
            encoding="utf-8",
        )
        latest = tmp_path / "policy-first-memory-1.0.0-synthesis.json"
        latest.write_text(
            json.dumps(make_prd(feature_name="Latest Feature").model_dump()),
            encoding="utf-8",
        )

        latest.touch()

        assert find_latest_prd() == latest

    def test_run_user_story_planning_loads_requested_story_from_legacy_prd(self, tmp_path, monkeypatch):
        payload = make_prd(
            feature_name="Memory Fabric",
            objective="Plan valid selected story from legacy artifact",
            user_stories=[
                UserStory(
                    id="US-001",
                    title="Valid story",
                    description="Plan me",
                    acceptance_criteria=["A", "B", "C"],
                    effort="M",
                    dependencies=[],
                ),
                UserStory(
                    id="US-002",
                    title="Another valid story",
                    description="Ignore me",
                    acceptance_criteria=["D", "E", "F"],
                    effort="S",
                    dependencies=[],
                ),
            ],
        ).model_dump()
        payload["user_stories"].append(
            {
                "id": "US-008",
                "title": "Broken legacy story",
                "description": "Malformed legacy acceptance criteria",
                "acceptance_criteria": ["Golden dataset owner defined.", "effort "],
                "effort": "M",
                "dependencies": [],
            }
        )
        prd_path = tmp_path / "policy-first-memory-1.0.0-synthesis.json"
        prd_path.write_text(json.dumps(payload), encoding="utf-8")
        monkeypatch.setattr(planning_flow, "OUTPUT_DIR", str(tmp_path))

        plan = UserStoryExecutionPlan(
            user_story_id="US-001",
            user_story_title="Valid story",
            approach_summary="Minimal plan",
            tasks=[make_task()],
            quality_score=8.6,
            final_validation_notes="Approved",
        )

        class FakeCrew:
            def kickoff(self):
                return type("CrewResult", (), {"pydantic": plan})()

        monkeypatch.setattr(planning_flow, "build_planning_crew", lambda **kwargs: FakeCrew())

        result = planning_flow.run_user_story_planning(
            prd_path=str(prd_path),
            user_story_ref="US-001",
            vision_context=VisionContext.PROJECT,
        )

        assert result["plan"]["user_story_id"] == "US-001"
