"""Tests for execution checkpointing and resume behavior."""

from __future__ import annotations

import json

from tests.conftest import make_plan, make_task
from execution import dialectic_execution as de
from schemas import ExecutionCheckpoint, TaskExecutionResult


def _write_plan(tmp_path):
    plan = make_plan(tasks=[make_task(id="T-001", title="First task")])
    path = tmp_path / "prd_output" / "exec_US-001_test.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan.model_dump(), indent=2), encoding="utf-8")
    return plan, str(path)


def test_run_dialectic_execution_writes_checkpoint_and_flow_ids(tmp_path, monkeypatch):
    plan, plan_path = _write_plan(tmp_path)

    class FakeFlow:
        def __init__(self, persistence=None):
            self.flow_id = "task-flow-1"

        def kickoff(self, inputs=None):
            return TaskExecutionResult(
                task_id="T-001",
                title="First task",
                success=True,
                score=9.2,
                retry_count=0,
                output_summary="implemented",
                execution_phases=["dialectic", "verify"],
            )

    monkeypatch.setattr(de, "TaskExecutionFlow", FakeFlow)
    monkeypatch.setattr(de, "_get_task_persistence", lambda: object())
    monkeypatch.setattr(de, "update_user_story_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(de, "update_task_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(de, "_run_verification", lambda *args, **kwargs: {"verified": True, "score": 9.5, "notes": "ok"})
    monkeypatch.setattr(de, "_load_prd_for_plan", lambda *args, **kwargs: None)
    monkeypatch.setattr(de, "_extract_acceptance_criteria", lambda *args, **kwargs: [])

    result = de.run_dialectic_execution(plan_path=plan_path, output_dir=str(tmp_path / "exec_output"))

    checkpoint_path = tmp_path / "exec_output" / result["run_id"] / "checkpoint.json"
    assert checkpoint_path.exists()
    checkpoint = ExecutionCheckpoint.model_validate_json(checkpoint_path.read_text(encoding="utf-8"))
    assert checkpoint.task_flow_ids == {"T-001": "task-flow-1"}
    assert result["task_flow_ids"] == {"T-001": "task-flow-1"}
    assert checkpoint.plan_id == plan.user_story_id


def test_resume_run_reuses_checkpointed_results_without_reexecuting(tmp_path, monkeypatch):
    plan, plan_path = _write_plan(tmp_path)
    run_id = "resume-001"
    run_dir = tmp_path / "exec_output" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = ExecutionCheckpoint(
        plan_id=plan.user_story_id,
        plan_title=plan.user_story_title,
        run_id=run_id,
        plan_path=str((tmp_path / "prd_output" / "exec_US-001_test.json").resolve()),
        vision_context="project",
        task_results=[
            TaskExecutionResult(
                task_id="T-001",
                title="First task",
                success=True,
                score=9.0,
                retry_count=0,
                output_summary="implemented",
                execution_phases=["dialectic", "verify"],
            )
        ],
        task_flow_ids={"T-001": "task-flow-1"},
        completed_outputs={"T-001": "implemented"},
    )
    (run_dir / "checkpoint.json").write_text(checkpoint.model_dump_json(indent=2), encoding="utf-8")

    monkeypatch.setattr(de, "TaskExecutionFlow", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("flow should not rerun")))
    monkeypatch.setattr(de, "update_user_story_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(de, "update_task_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(de, "_run_verification", lambda *args, **kwargs: {"verified": True, "score": 9.5, "notes": "ok"})
    monkeypatch.setattr(de, "_load_prd_for_plan", lambda *args, **kwargs: None)
    monkeypatch.setattr(de, "_extract_acceptance_criteria", lambda *args, **kwargs: [])

    result = de.run_dialectic_execution(
        plan_path=plan_path,
        output_dir=str(tmp_path / "exec_output"),
        resume_run_id=run_id,
    )

    assert result["run_id"] == run_id
    assert result["task_flow_ids"] == {"T-001": "task-flow-1"}
    assert result["overall_success"] is True
