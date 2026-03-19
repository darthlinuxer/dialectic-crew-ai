"""Tests for target-scoped plan and execution artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import planning.flow as planning_flow
from tests.conftest import make_plan, make_prd, make_task
from dialectic.target import TargetConfig
from dialectic.vision import VisionContext
from execution import dialectic_execution as de
from schemas import TaskExecutionResult


def _target_config(app_root: Path, target_root: Path) -> TargetConfig:
    return TargetConfig(
        target_path=target_root,
        set_at=datetime(2026, 3, 14, 15, 0, tzinfo=timezone.utc),
        repo_name=target_root.name,
        repo_remote="git@github.com:octo/target-repo.git",
        vision_path=app_root
        / "knowledge"
        / "target"
        / "github-com-octo-target-repo--abc12345"
        / "VISION.md",
        target_slug="github-com-octo-target-repo--abc12345",
    )


def test_run_user_story_planning_saves_under_target_scope(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    target_root = tmp_path / "target-repo"
    app_root.mkdir()
    target_root.mkdir()
    target_config = _target_config(app_root, target_root)

    prd = make_prd(feature_name="Target Feature")
    prd_dir = app_root / "prd_output" / "targets" / target_config.target_slug
    prd_dir.mkdir(parents=True)
    prd_path = prd_dir / "target-feature-1.0.json"
    prd_path.write_text(prd.model_dump_json(indent=2), encoding="utf-8")

    class FakeCrew:
        def kickoff(self):
            return type(
                "CrewResult", (), {"pydantic": make_plan(tasks=[make_task()])}
            )()

    monkeypatch.setattr(
        planning_flow, "build_planning_crew", lambda **kwargs: FakeCrew()
    )
    monkeypatch.setattr(planning_flow, "MAX_PLAN_RETRIES", 0)
    monkeypatch.setattr(
        planning_flow, "resolve_prd_output_dir", lambda context: prd_dir
    )

    result = planning_flow.run_user_story_planning(
        prd_path=str(prd_path),
        user_story_ref=None,
        vision_context=VisionContext.PROJECT,
    )

    assert Path(result["plan_path_json"]).parent == prd_dir
    assert Path(result["plan_path_md"]).parent == prd_dir


def test_run_dialectic_execution_uses_target_scope_and_repo_cwd(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    target_root = tmp_path / "target-repo"
    prd_dir = (
        app_root / "prd_output" / "targets" / "github-com-octo-target-repo--abc12345"
    )
    app_root.mkdir()
    target_root.mkdir()
    prd_dir.mkdir(parents=True)

    plan = make_plan(tasks=[make_task(id="T-001", title="First task")])
    plan_path = prd_dir / "exec_US-001_test.json"
    plan_path.write_text(json.dumps(plan.model_dump(), indent=2), encoding="utf-8")

    cwd_seen: list[Path] = []

    class FakeFlow:
        def __init__(self, persistence=None):
            self.flow_id = "task-flow-1"

        def kickoff(self, inputs=None):
            cwd_seen.append(Path.cwd())
            return TaskExecutionResult(
                task_id="T-001",
                title="First task",
                success=True,
                score=9.2,
                retry_count=0,
                output_summary="implemented",
                execution_phases=["dialectic", "verify"],
            )

    exec_dir = (
        app_root / "exec_output" / "targets" / "github-com-octo-target-repo--abc12345"
    )
    monkeypatch.setattr(de, "TaskExecutionFlow", FakeFlow)
    monkeypatch.setattr(de, "_get_task_persistence", lambda: object())
    monkeypatch.setattr(de, "update_user_story_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(de, "update_task_status", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        de,
        "_run_verification",
        lambda *args, **kwargs: {"verified": True, "score": 9.5, "notes": "ok"},
    )
    monkeypatch.setattr(de, "_load_prd_for_plan", lambda *args, **kwargs: None)
    monkeypatch.setattr(de, "_extract_acceptance_criteria", lambda *args, **kwargs: [])
    monkeypatch.setattr(de, "resolve_exec_output_dir", lambda context: exec_dir)
    monkeypatch.setattr(de, "resolve_execution_root", lambda: target_root)

    original_cwd = Path.cwd()
    result = de.run_dialectic_execution(plan_path=str(plan_path))

    assert Path(result["output_path"]).parent == exec_dir
    assert cwd_seen == [target_root]
    assert Path.cwd() == original_cwd
