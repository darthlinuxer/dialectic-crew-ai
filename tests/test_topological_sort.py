"""Tests for extracted execution ordering and context helpers."""

import pytest

from tests.conftest import make_task
from execution.context_builder import build_task_context
from execution.topological_sort import topological_sort


class TestTopologicalSort:
    def test_no_dependencies(self):
        tasks = [
            make_task(id="T-001", order=1),
            make_task(id="T-002", order=2),
        ]
        result = topological_sort(tasks)
        ids = [t.id for t in result]
        assert ids == ["T-001", "T-002"]

    def test_linear_chain(self):
        tasks = [
            make_task(id="T-002", order=2, dependencies=["T-001"]),
            make_task(id="T-001", order=1),
        ]
        result = topological_sort(tasks)
        ids = [t.id for t in result]
        assert ids.index("T-001") < ids.index("T-002")

    def test_diamond_dependency(self):
        tasks = [
            make_task(id="T-001", order=1),
            make_task(id="T-002", order=2, dependencies=["T-001"]),
            make_task(id="T-003", order=2, dependencies=["T-001"]),
            make_task(id="T-004", order=3, dependencies=["T-002", "T-003"]),
        ]
        result = topological_sort(tasks)
        ids = [t.id for t in result]
        assert ids.index("T-001") < ids.index("T-002")
        assert ids.index("T-001") < ids.index("T-003")
        assert ids.index("T-002") < ids.index("T-004")
        assert ids.index("T-003") < ids.index("T-004")

    def test_circular_dependencies_raise(self):
        tasks = [
            make_task(id="T-001", order=1, dependencies=["T-002"]),
            make_task(id="T-002", order=2, dependencies=["T-001"]),
        ]

        with pytest.raises(ValueError, match="circular dependencies"):
            topological_sort(tasks)

    def test_self_dependency_raises(self):
        tasks = [make_task(id="T-001", order=1, dependencies=["T-001"])]

        with pytest.raises(ValueError, match="self-dependency"):
            topological_sort(tasks)

    def test_single_task(self):
        tasks = [make_task(id="T-001")]
        result = topological_sort(tasks)
        assert len(result) == 1
        assert result[0].id == "T-001"

    def test_unknown_dependencies_raise(self):
        tasks = [
            make_task(id="T-001", order=1, dependencies=["T-999"]),
            make_task(id="T-002", order=2),
        ]

        with pytest.raises(ValueError, match="unknown dependencies"):
            topological_sort(tasks)


class TestBuildTaskContext:
    def test_no_previous_outputs(self, sample_plan, sample_task):
        ctx = build_task_context(sample_plan, {}, sample_task)
        assert "No previous tasks yet" in ctx
        assert sample_task.id in ctx
        assert sample_plan.user_story_id in ctx
        assert "Definition of done" in ctx
        assert "imports resolve" in ctx
        assert "related tests or exports" in ctx

    def test_with_previous_outputs(self, sample_plan, sample_task):
        completed = {"T-000": "Created the config file at /path/to/config.yaml"}
        ctx = build_task_context(sample_plan, completed, sample_task)
        assert "T-000" in ctx
        assert "config.yaml" in ctx

    def test_truncates_long_outputs(self, sample_plan, sample_task):
        completed = {"T-000": "x" * 3000}
        ctx = build_task_context(sample_plan, completed, sample_task)
        assert "..." in ctx
