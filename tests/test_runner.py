"""Tests for execution/runner.py — artifact generation and plan loading."""

import json
import os

import pytest

from schemas import UserStoryExecutionPlan
from execution.runner import (
    _artifact_markdown,
    _load_plan,
    _find_latest_plan,
    run_execution,
)
from tests.conftest import make_plan, make_task


class TestArtifactMarkdown:
    def test_contains_story_info(self, sample_plan):
        md = _artifact_markdown(sample_plan)
        assert "US-001" in md
        assert "Sample Story" in md

    def test_contains_task_sections(self):
        plan = make_plan(
            tasks=[
                make_task(id="T-001", title="First", order=1),
                make_task(id="T-002", title="Second", order=2, dependencies=["T-001"]),
            ]
        )
        md = _artifact_markdown(plan)
        assert "T-001" in md
        assert "T-002" in md
        assert "Dependencies" in md

    def test_contains_approach(self, sample_plan):
        md = _artifact_markdown(sample_plan)
        assert "Approach" in md
        assert sample_plan.approach_summary in md

    def test_risks_and_notes(self, sample_plan):
        md = _artifact_markdown(sample_plan)
        assert "Data loss" in md
        assert "PostgreSQL" in md


class TestLoadPlan:
    def test_load_valid(self, plan_file):
        plan = _load_plan(plan_file)
        assert isinstance(plan, UserStoryExecutionPlan)
        assert plan.user_story_id == "US-001"

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            _load_plan("/nonexistent/path.json")


class TestFindLatestPlan:
    def test_finds_latest(self, tmp_path):
        d = tmp_path / "prd_output"
        d.mkdir()
        plan = make_plan()

        old_file = d / "exec_US-001_20260101.json"
        new_file = d / "exec_US-001_20260102.json"
        old_file.write_text(json.dumps(plan.model_dump(), indent=2), encoding="utf-8")
        new_file.write_text(json.dumps(plan.model_dump(), indent=2), encoding="utf-8")
        os.utime(old_file, (1000000, 1000000))
        os.utime(new_file, (2000000, 2000000))

        from execution import runner
        original = runner.PRD_OUTPUT_DIR
        runner.PRD_OUTPUT_DIR = str(d)
        try:
            found = _find_latest_plan()
            assert "20260102" in found.name
        finally:
            runner.PRD_OUTPUT_DIR = original

    def test_raises_on_empty_dir(self, tmp_path):
        d = tmp_path / "prd_output"
        d.mkdir()

        from execution import runner
        original = runner.PRD_OUTPUT_DIR
        runner.PRD_OUTPUT_DIR = str(d)
        try:
            with pytest.raises(FileNotFoundError, match="No execution plan"):
                _find_latest_plan()
        finally:
            runner.PRD_OUTPUT_DIR = original


class TestRunExecution:
    def test_with_plan_dict(self, tmp_path):
        plan = make_plan()
        result = run_execution(plan=plan.model_dump(), output_dir=str(tmp_path))
        assert result["success"] is True
        assert result["plan_id"] == "US-001"
        assert os.path.exists(result["output_path"])

    def test_with_plan_object(self, tmp_path):
        plan = make_plan()
        result = run_execution(plan=plan, output_dir=str(tmp_path))
        assert result["success"] is True
        assert os.path.exists(result["output_path"])
        content = open(result["output_path"], encoding="utf-8").read()
        assert "US-001" in content
