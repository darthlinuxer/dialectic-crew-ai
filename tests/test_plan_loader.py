"""Tests for execution.plan_loader shared helpers."""

import json
import os

import pytest

from execution.plan_loader import find_latest_plan, load_plan
from schemas import UserStoryExecutionPlan
from conftest import make_plan


class TestFindLatestPlan:
    def test_finds_latest_exec_plan(self, tmp_path):
        plan = make_plan()
        old_file = tmp_path / "exec_US-001_20260101.json"
        new_file = tmp_path / "exec_US-001_20260102.json"

        old_file.write_text(json.dumps(plan.model_dump(), indent=2), encoding="utf-8")
        new_file.write_text(json.dumps(plan.model_dump(), indent=2), encoding="utf-8")
        os.utime(old_file, (1000000, 1000000))
        os.utime(new_file, (2000000, 2000000))

        found = find_latest_plan(tmp_path)

        assert found == new_file

    def test_raises_when_directory_missing(self, tmp_path):
        missing = tmp_path / "does-not-exist"

        with pytest.raises(FileNotFoundError, match="Directory"):
            find_latest_plan(missing)

    def test_raises_when_no_exec_plans_exist(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="No execution plan"):
            find_latest_plan(tmp_path)


class TestLoadPlan:
    def test_loads_valid_plan_json(self, tmp_path):
        plan = make_plan()
        plan_path = tmp_path / "exec_US-001_20260102.json"
        plan_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")

        loaded = load_plan(plan_path)

        assert isinstance(loaded, UserStoryExecutionPlan)
        assert loaded.user_story_id == plan.user_story_id

    def test_raises_for_missing_plan(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_plan(tmp_path / "missing.json")