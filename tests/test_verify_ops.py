"""Tests for execution verify/status helpers and acceptance criteria."""

import pytest

from execution.status import (
    load_plan,
    save_plan,
    find_task,
    mark_task,
    update_task_status,
    update_user_story_status,
    show_status,
)
from execution.verify import (
    _load_prd_for_plan,
    _run_verification,
    _extract_acceptance_criteria,
)
from conftest import make_plan, make_task, make_prd


class TestLoadSavePlan:
    def test_roundtrip(self, tmp_path):
        plan = make_plan()
        path = str(tmp_path / "plan.json")
        save_plan(plan, path)
        loaded, resolved = load_plan(path)
        assert loaded.user_story_id == plan.user_story_id
        assert resolved == path

    def test_load_missing(self):
        with pytest.raises(FileNotFoundError):
            load_plan("/nonexistent.json")


class TestFindTask:
    def test_found(self, sample_plan):
        t = find_task(sample_plan, "T-001")
        assert t.id == "T-001"

    def test_case_insensitive(self, sample_plan):
        t = find_task(sample_plan, "t-001")
        assert t.id == "T-001"

    def test_not_found(self, sample_plan):
        with pytest.raises(ValueError, match="not found"):
            find_task(sample_plan, "T-999")


class TestMarkTask:
    def test_mark_completed(self, plan_file):
        result = mark_task("T-001", "completed", plan_path=plan_file, notes="done")
        assert result["status"] == "completed"
        loaded, _ = load_plan(plan_file)
        task = find_task(loaded, "T-001")
        assert task.status == "completed"
        assert task.completed_at is not None
        assert task.verification_notes == "done"

    def test_mark_pending_clears_completed_at(self, plan_file):
        mark_task("T-001", "completed", plan_path=plan_file)
        mark_task("T-001", "pending", plan_path=plan_file)
        loaded, _ = load_plan(plan_file)
        task = find_task(loaded, "T-001")
        assert task.status == "pending"
        assert task.completed_at is None


class TestUpdateTaskStatus:
    def test_programmatic_update(self, plan_file):
        update_task_status(plan_file, "T-001", "in_progress", notes="started")
        loaded, _ = load_plan(plan_file)
        task = find_task(loaded, "T-001")
        assert task.status == "in_progress"
        assert task.verification_notes == "started"


class TestUpdateUserStoryStatus:
    def test_set_completed(self, plan_file):
        update_user_story_status(plan_file, "completed")
        loaded, _ = load_plan(plan_file)
        assert loaded.status == "completed"
        assert loaded.completed_at is not None

    def test_set_in_progress_clears_completed_at(self, plan_file):
        update_user_story_status(plan_file, "completed")
        update_user_story_status(plan_file, "in_progress")
        loaded, _ = load_plan(plan_file)
        assert loaded.status == "in_progress"
        assert loaded.completed_at is None


class TestShowStatus:
    def test_returns_summary(self, plan_file):
        result = show_status(plan_path=plan_file)
        assert result["total"] == 1
        assert result["story_status"] == "pending"
        assert "pending" in result


class TestExtractAcceptanceCriteria:
    def test_match_by_id(self, sample_plan):
        prd = make_prd()
        criteria = _extract_acceptance_criteria(sample_plan, prd)
        assert criteria == ["AC1", "AC2", "AC3"]

    def test_no_match(self):
        plan = make_plan(user_story_id="US-999")
        prd = make_prd()
        criteria = _extract_acceptance_criteria(plan, prd)
        assert criteria == []

    def test_no_prd(self, sample_plan):
        criteria = _extract_acceptance_criteria(sample_plan, None)
        assert criteria == []


class TestLoadPrdForPlan:
    def test_prefers_source_prd_path(self, tmp_path):
        prd = make_prd(feature_name="Linked PRD")
        prd_path = tmp_path / "linked_prd.json"
        prd_path.write_text(prd.model_dump_json(indent=2), encoding="utf-8")

        plan = make_plan(source_prd_path=str(prd_path))

        loaded = _load_prd_for_plan(plan, None)

        assert loaded is not None
        assert loaded.feature_name == "Linked PRD"


class TestRunVerification:
    def test_uses_runtime_builder_and_task_output_pydantic(self, monkeypatch):
        from schemas import ValidationOutput

        class FakeCrew:
            def kickoff(self):
                task_output = type("TaskOutput", (), {"pydantic": ValidationOutput(quality_score=8.5, consensus_reached=True, final_validation_notes="looks good")})()
                return type("CrewResult", (), {"pydantic": None, "tasks_output": [task_output]})()

        captured: dict = {}

        def fake_build_verification_crew(*, task, acceptance_criteria, vision_context):
            captured["task"] = task
            captured["acceptance_criteria"] = acceptance_criteria
            captured["vision_context"] = vision_context
            return FakeCrew()

        monkeypatch.setattr("execution.verify.build_verification_crew", fake_build_verification_crew)

        task = make_task(id="T-001", title="Ship feature", description="Implement feature")
        result = _run_verification(task, ["AC1"])

        assert captured["task"].id == "T-001"
        assert captured["acceptance_criteria"] == ["AC1"]
        assert result == {
            "task_id": "T-001",
            "verified": True,
            "score": 8.5,
            "notes": "looks good",
        }

    def test_returns_failure_when_structured_result_missing(self, monkeypatch):
        class FakeCrew:
            def kickoff(self):
                return type("CrewResult", (), {"pydantic": None, "tasks_output": [], "raw": "not-json"})()

        monkeypatch.setattr(
            "execution.verify.build_verification_crew",
            lambda **kwargs: FakeCrew(),
        )

        task = make_task(id="T-404", title="Missing", description="Nothing there")
        result = _run_verification(task, ["AC1"])

        assert result["task_id"] == "T-404"
        assert result["verified"] is False
        assert result["score"] == 0.0
        assert "Failed to obtain structured result" in result["notes"]
