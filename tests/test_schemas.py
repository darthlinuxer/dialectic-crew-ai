"""Tests for Pydantic schema validation in schemas.py."""

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=too-few-public-methods

from typing import Any, cast

import pytest
from pydantic import ValidationError

from schemas import (
    UserStory,
    MacroImpact,
    AntiDriftQuestion,
    PRDSchema,
    ValidationOutput,
    VerificationResult,
    TaskExecutionResult,
    ExecutionReport,
    ExecutionCheckpoint,
    SelfImprovementRecord,
)
from tests.conftest import make_prd, make_task, make_plan


class TestUserStory:
    def test_valid(self):
        us = UserStory(
            id="US-001",
            title="Login",
            description="User can log in",
            acceptance_criteria=["AC1", "AC2", "AC3"],
            effort="M",
        )
        assert us.id == "US-001"
        assert us.dependencies == []

    def test_acceptance_criteria_min_length(self):
        with pytest.raises(ValidationError, match="acceptance_criteria"):
            UserStory(
                id="US-001",
                title="Login",
                description="...",
                acceptance_criteria=["AC1", "AC2"],
                effort="M",
            )

    def test_invalid_effort(self):
        with pytest.raises(ValidationError, match="effort"):
            UserStory(
                id="US-001",
                title="Login",
                description="...",
                acceptance_criteria=["AC1", "AC2", "AC3"],
                effort=cast(Any, "HUGE"),
            )

    def test_acceptance_criteria_entries_are_trimmed(self):
        us = UserStory(
            id="US-001",
            title="Login",
            description="...",
            acceptance_criteria=["  AC1  ", "AC2", " AC3"],
            effort="M",
        )

        assert us.acceptance_criteria == ["AC1", "AC2", "AC3"]

    def test_acceptance_criteria_reject_placeholder_labels(self):
        with pytest.raises(ValidationError, match="acceptance_criteria"):
            UserStory(
                id="US-001",
                title="Login",
                description="...",
                acceptance_criteria=["AC1", "AC2", "effort "],
                effort="M",
            )


class TestMacroImpact:
    def test_valid(self):
        mi = MacroImpact(
            modules_affected=["auth"],
            risk_level="HIGH",
            performance_impact="significant",
            security_impact="high",
        )
        assert mi.risk_level == "HIGH"

    def test_invalid_risk_level(self):
        with pytest.raises(ValidationError, match="risk_level"):
            MacroImpact(
                modules_affected=["auth"],
                risk_level=cast(Any, "EXTREME"),
                performance_impact="...",
                security_impact="...",
            )


class TestPRDSchema:
    def test_valid(self):
        prd = make_prd()
        assert prd.feature_name == "Test Feature"

    def test_min_user_stories(self):
        with pytest.raises(ValidationError, match="user_stories"):
            make_prd(user_stories=[])

    def test_min_anti_drift_questions(self):
        adq = [AntiDriftQuestion(question="q", answer="a") for _ in range(4)]
        with pytest.raises(ValidationError, match="anti_drift_questions"):
            make_prd(anti_drift_questions=adq)

    def test_quality_score_upper_bound(self):
        with pytest.raises(ValidationError, match="quality_score"):
            make_prd(quality_score=11.0)

    def test_quality_score_lower_bound(self):
        with pytest.raises(ValidationError, match="quality_score"):
            make_prd(quality_score=-1.0)

    def test_model_dump_roundtrip(self):
        prd = make_prd()
        data = prd.model_dump()
        prd2 = PRDSchema.model_validate(data)
        assert prd2.feature_name == prd.feature_name
        assert len(prd2.user_stories) == len(prd.user_stories)

    def test_supports_roadmap_provenance_fields(self):
        prd = make_prd(
            source_roadmap_path="internal/ROADMAP.md",
            source_roadmap_label="Expose output-format selection through the CLI/runtime UX",
            source_roadmap_key="expose output-format selection through the cli/runtime ux",
        )

        assert prd.source_roadmap_path == "internal/ROADMAP.md"
        assert (
            prd.source_roadmap_label
            == "Expose output-format selection through the CLI/runtime UX"
        )
        assert (
            prd.source_roadmap_key
            == "expose output-format selection through the cli/runtime ux"
        )


class TestImplementationTask:
    def test_defaults(self):
        t = make_task()
        assert t.status == "pending"
        assert t.completed_at is None
        assert t.verification_notes == ""
        assert t.acceptance_checks == []

    def test_invalid_status(self):
        with pytest.raises(ValidationError, match="status"):
            make_task(status="unknown")


class TestUserStoryExecutionPlan:
    def test_valid(self):
        plan = make_plan()
        assert plan.user_story_id == "US-001"
        assert plan.status == "pending"

    def test_min_tasks(self):
        with pytest.raises(ValidationError, match="tasks"):
            make_plan(tasks=[])

    def test_quality_score_bounds(self):
        with pytest.raises(ValidationError, match="quality_score"):
            make_plan(quality_score=11.0)

    def test_supports_roadmap_provenance_fields(self):
        plan = make_plan(
            source_roadmap_path="internal/ROADMAP.md",
            source_roadmap_label="Expose output-format selection through the CLI/runtime UX",
            source_roadmap_key="expose output-format selection through the cli/runtime ux",
        )

        assert plan.source_roadmap_path == "internal/ROADMAP.md"
        assert (
            plan.source_roadmap_label
            == "Expose output-format selection through the CLI/runtime UX"
        )
        assert (
            plan.source_roadmap_key
            == "expose output-format selection through the cli/runtime ux"
        )


class TestValidationOutput:
    def test_defaults(self):
        vo = ValidationOutput(quality_score=8.0)
        assert vo.consensus_reached is False
        assert vo.final_validation_notes == ""

    def test_score_bounds(self):
        with pytest.raises(ValidationError, match="quality_score"):
            ValidationOutput(quality_score=11.0)


class TestVerificationResult:
    def test_defaults(self):
        vr = VerificationResult()
        assert vr.verified is False
        assert vr.checks_passed == []
        assert vr.checks_failed == []


class TestTaskExecutionResult:
    def test_construction(self):
        r = TaskExecutionResult(
            task_id="T-001",
            title="Test",
            success=True,
            score=9.0,
            retry_count=0,
        )
        assert r.output_paths == []
        assert r.verification is None


class TestExecutionReport:
    def test_construction(self):
        report = ExecutionReport(
            plan_id="US-001",
            plan_title="Story",
            run_id="20260101",
        )
        assert report.overall_success is False
        assert report.task_results == []
        assert report.task_flow_ids == {}

    def test_supports_roadmap_provenance_fields(self):
        report = ExecutionReport(
            plan_id="US-001",
            plan_title="Story",
            run_id="20260101",
            source_roadmap_path="internal/ROADMAP.md",
            source_roadmap_label="Expose output-format selection through the CLI/runtime UX",
            source_roadmap_key="expose output-format selection through the cli/runtime ux",
        )

        assert report.source_roadmap_path == "internal/ROADMAP.md"
        assert (
            report.source_roadmap_label
            == "Expose output-format selection through the CLI/runtime UX"
        )
        assert (
            report.source_roadmap_key
            == "expose output-format selection through the cli/runtime ux"
        )


class TestExecutionCheckpoint:
    def test_construction(self):
        checkpoint = ExecutionCheckpoint(
            plan_id="US-001",
            plan_title="Story",
            run_id="20260101",
            plan_path="/tmp/plan.json",
            vision_context="project",
        )
        assert checkpoint.task_results == []
        assert checkpoint.task_flow_ids == {}


class TestSelfImprovementRecordResumeMetadata:
    def test_defaults(self):
        record = SelfImprovementRecord(
            cycle_id="cycle-1",
            timestamp="2026-03-10T00:00:00Z",
        )
        assert record.prd_flow_id == ""
        assert record.execution_task_flow_ids == {}
        assert record.continue_prd is False
        assert record.continue_prd_source_prd_path == ""
        assert record.continue_prd_current_story_ref == ""
        assert record.continue_prd_completed_story_refs == []
        assert record.continue_prd_story_history == []

    def test_supports_continue_prd_loop_state_roundtrip(self):
        record = SelfImprovementRecord(
            cycle_id="cycle-continue-prd",
            timestamp="2026-03-10T00:00:00Z",
            continue_prd=True,
            continue_prd_source_prd_path="prd_output/self/input_prd.json",
            continue_prd_current_story_ref="US2",
            continue_prd_completed_story_refs=["US1"],
            continue_prd_story_history=[
                {
                    "story_ref": "US1",
                    "plan_path_json": "prd_output/self/exec_US1.json",
                    "execution_run_id": "run-us1",
                    "story_status": "completed",
                }
            ],
        )

        restored = SelfImprovementRecord.model_validate(record.model_dump())

        assert restored.continue_prd is True
        assert restored.continue_prd_source_prd_path == "prd_output/self/input_prd.json"
        assert restored.continue_prd_current_story_ref == "US2"
        assert restored.continue_prd_completed_story_refs == ["US1"]
        assert restored.continue_prd_story_history == [
            {
                "story_ref": "US1",
                "plan_path_json": "prd_output/self/exec_US1.json",
                "execution_run_id": "run-us1",
                "story_status": "completed",
            }
        ]
