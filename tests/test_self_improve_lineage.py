"""Focused tests for self-improve artifact lineage and stage validation."""

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=redefined-outer-name,unused-argument,too-few-public-methods
# pylint: disable=line-too-long,duplicate-code

from unittest.mock import MagicMock, patch

import pytest

from dialectic.metrics import MetricsStore, _reset_metrics_store
from dialectic.vision import VisionContext
from main.self_improve import _build_pr_body, _save_self_improve_record, run_self_improve
from schemas import ImprovementOpportunity, IntrospectionReport, SelfImprovementRecord


@pytest.fixture(autouse=True)
def _reset_singleton():
    _reset_metrics_store()
    yield
    _reset_metrics_store()


@pytest.fixture
def store(tmp_path):
    return MetricsStore(db_path=tmp_path / "test_self_improve_lineage.db")


@pytest.fixture
def vision_file(tmp_path):
    vision = tmp_path / "internal" / "SELF_VISION.md"
    vision.parent.mkdir(parents=True, exist_ok=True)
    vision.write_text("- [ ] Track lineage across self-improve stages\n")
    return vision


@pytest.fixture
def configured_env(tmp_path, monkeypatch, store, vision_file):
    monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
    monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
    monkeypatch.setattr("main.self_improve._git_worktree_clean", lambda cwd: (True, "clean"))
    monkeypatch.setattr(
        "main.self_improve._git_commit_all",
        lambda cwd, message: (False, "nothing to commit"),
    )
    monkeypatch.setattr(
        "main.self_improve._git_has_commits_ahead",
        lambda cwd, base_branch="main": (True, f"1 commit ahead of {base_branch}"),
    )
    monkeypatch.setattr(
        "main.self_improve._snapshot_tests",
        lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
    )
    monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision_file)
    monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
    monkeypatch.setattr("main.self_improve.dialectic_prioritize", lambda opps, **kw: opps)
    monkeypatch.setattr("main.self_improve._git_branch_create", lambda b, c: True)
    monkeypatch.setattr("main.self_improve._git_discard_branch", lambda b, c: None)
    monkeypatch.setattr("main.self_improve._create_pr", lambda *args, **kwargs: None)
    return tmp_path


class TestSelfImproveLineage:
    def test_records_artifact_lineage_on_success(self, configured_env):
        tmp_path = configured_env
        mock_flow = MagicMock()
        mock_flow.flow_id = "prd-flow-123"
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = str(tmp_path / "prd_output" / "PRD_test.json")
        mock_flow.state.prd_path_md = str(tmp_path / "prd_output" / "PRD_test.md")

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": str(tmp_path / "prd_output" / "exec_test.json"),
            "plan_path_md": str(tmp_path / "prd_output" / "exec_test.md"),
        }
        mock_exec = {
            "overall_success": True,
            "story_status": "completed",
            "run_id": "run-123",
            "task_flow_ids": {"T-001": "task-flow-1"},
            "output_path": str(tmp_path / "exec_output" / "run-123"),
            "report_path": str(tmp_path / "exec_output" / "run-123" / "report.json"),
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(max_improvements=1)

        assert record.prd_flow_id == "prd-flow-123"
        assert record.prd_path_json == mock_flow.state.prd_path_json
        assert record.prd_path_md == mock_flow.state.prd_path_md
        assert record.plan_path_json == mock_plan["plan_path_json"]
        assert record.plan_path_md == mock_plan["plan_path_md"]
        assert record.execution_run_id == mock_exec["run_id"]
        assert record.execution_task_flow_ids == mock_exec["task_flow_ids"]
        assert record.execution_output_path == mock_exec["output_path"]
        assert record.execution_report_path == mock_exec["report_path"]

    def test_aborts_when_plan_path_missing(self, configured_env):
        mock_flow = MagicMock()
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = "prd_output/PRD_test.json"
        mock_flow.state.prd_path_md = "prd_output/PRD_test.md"

        mock_plan = {"quality_score": 9.0, "plan_path_json": "", "plan_path_md": ""}

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    record = run_self_improve(max_improvements=1)

        assert "Planning did not produce an exported artifact" in record.failure_reason

    def test_aborts_when_execution_report_missing(self, configured_env):
        tmp_path = configured_env
        mock_flow = MagicMock()
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = str(tmp_path / "prd_output" / "PRD_test.json")
        mock_flow.state.prd_path_md = str(tmp_path / "prd_output" / "PRD_test.md")

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": str(tmp_path / "prd_output" / "exec_test.json"),
            "plan_path_md": str(tmp_path / "prd_output" / "exec_test.md"),
        }
        mock_exec = {
            "overall_success": True,
            "story_status": "completed",
            "run_id": "run-123",
            "output_path": str(tmp_path / "exec_output" / "run-123"),
            "report_path": "",
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(max_improvements=1)

        assert "Execution report did not produce an exported artifact" in record.failure_reason

    def test_resume_reuses_artifacts_and_execution_checkpoint_without_git(self, configured_env, monkeypatch):
        tmp_path = configured_env
        opportunity = ImprovementOpportunity(
            id="opp-1",
            category="code_health",
            title="Resume interrupted execution",
            description="Continue from the saved execution checkpoint.",
            evidence=["exec_output/run-123/checkpoint.json"],
            estimated_impact="high",
        )
        record = SelfImprovementRecord(
            cycle_id="cycle-resume",
            timestamp="2026-03-10T00:00:00Z",
            baseline_metrics={"prd_score": {"count": 0, "mean": 0}},
            selected_opportunities=[opportunity],
            opportunities_found=1,
            opportunities_attempted=1,
            prd_generated=True,
            plan_generated=True,
            execution_attempted=False,
            branch_name="self-improve/cycle-resume",
            feature_request="[Self-Improvement] Resume interrupted execution",
            prd_flow_id="prd-flow-123",
            prd_path_json=str(tmp_path / "prd_output" / "PRD_test.json"),
            plan_path_json=str(tmp_path / "prd_output" / "exec_test.json"),
            execution_run_id="run-123",
        )
        _save_self_improve_record(tmp_path, record)

        monkeypatch.setattr(
            "main.self_improve._command_available",
            lambda command: command != "git",
        )
        monkeypatch.setattr("main.self_improve._create_pr", lambda *args, **kwargs: None)

        exec_calls = []

        def fake_execution(**kwargs):
            exec_calls.append(kwargs)
            return {
                "overall_success": True,
                "story_status": "completed",
                "run_id": "run-123",
                "task_flow_ids": {"T-001": "task-flow-1"},
                "output_path": str(tmp_path / "exec_output" / "run-123"),
                "report_path": str(tmp_path / "exec_output" / "run-123" / "report.json"),
            }

        with patch("execution.dialectic_execution.run_dialectic_execution", side_effect=fake_execution):
            resumed = run_self_improve(resume_cycle_id="cycle-resume")

        assert resumed.failure_reason == ""
        assert resumed.execution_run_id == "run-123"
        assert exec_calls == [{
            "plan_path": str(tmp_path / "prd_output" / "exec_test.json"),
            "vision_context": VisionContext.SELF,
            "resume_run_id": "run-123",
        }]

    def test_resume_after_execution_failure_clears_stale_failure_and_skips_completed_stages(
        self,
        configured_env,
        monkeypatch,
    ):
        tmp_path = configured_env
        opportunity = ImprovementOpportunity(
            id="opp-1",
            category="code_health",
            title="Recover failed execution",
            description="Resume only the unfinished execution stage.",
            evidence=["exec_output/run-123/checkpoint.json"],
            estimated_impact="high",
        )
        record = SelfImprovementRecord(
            cycle_id="cycle-failed-exec",
            timestamp="2026-03-10T00:00:00Z",
            baseline_metrics={"prd_score": {"count": 0, "mean": 0}},
            selected_opportunities=[opportunity],
            opportunities_found=1,
            opportunities_attempted=1,
            prd_generated=True,
            plan_generated=True,
            execution_attempted=True,
            branch_name="self-improve/cycle-failed-exec",
            feature_request="[Self-Improvement] Recover failed execution",
            prd_flow_id="prd-flow-123",
            prd_path_json=str(tmp_path / "prd_output" / "PRD_test.json"),
            plan_path_json=str(tmp_path / "prd_output" / "exec_test.json"),
            execution_run_id="run-123",
            failure_reason="Execution failed: failed",
        )
        _save_self_improve_record(tmp_path, record)

        monkeypatch.setattr("main.self_improve._create_pr", lambda *args, **kwargs: None)

        def fail_if_called(*args, **kwargs):
            raise AssertionError("Completed upstream stage should not rerun on resume")

        exec_calls = []

        def fake_execution(**kwargs):
            exec_calls.append(kwargs)
            return {
                "overall_success": True,
                "story_status": "completed",
                "run_id": "run-123",
                "task_flow_ids": {"T-001": "task-flow-1"},
                "output_path": str(tmp_path / "exec_output" / "run-123"),
                "report_path": str(tmp_path / "exec_output" / "run-123" / "report.json"),
            }

        with patch("planning.flow.run_user_story_planning", side_effect=fail_if_called):
            with patch("dialectic.prd_flow.DialecticFlow", side_effect=fail_if_called):
                with patch("execution.dialectic_execution.run_dialectic_execution", side_effect=fake_execution):
                    resumed = run_self_improve(resume_cycle_id="cycle-failed-exec")

        assert resumed.failure_reason == ""
        assert resumed.execution_output_path.endswith("exec_output/run-123")
        assert exec_calls == [{
            "plan_path": str(tmp_path / "prd_output" / "exec_test.json"),
            "vision_context": VisionContext.SELF,
            "resume_run_id": "run-123",
        }]

    def test_resume_after_planning_failure_reuses_prd_and_runs_remaining_stages(
        self,
        configured_env,
        monkeypatch,
    ):
        tmp_path = configured_env
        opportunity = ImprovementOpportunity(
            id="opp-1",
            category="code_health",
            title="Recover failed planning",
            description="Resume from planning and continue execution.",
            evidence=["prd_output/PRD_test.json"],
            estimated_impact="medium",
        )
        record = SelfImprovementRecord(
            cycle_id="cycle-failed-plan",
            timestamp="2026-03-10T00:00:00Z",
            baseline_metrics={"prd_score": {"count": 0, "mean": 0}},
            selected_opportunities=[opportunity],
            opportunities_found=1,
            opportunities_attempted=1,
            prd_generated=True,
            plan_generated=False,
            execution_attempted=False,
            branch_name="self-improve/cycle-failed-plan",
            feature_request="[Self-Improvement] Recover failed planning",
            prd_flow_id="prd-flow-123",
            prd_path_json=str(tmp_path / "prd_output" / "PRD_test.json"),
            failure_reason="Plan quality too low: 6.0",
        )
        _save_self_improve_record(tmp_path, record)

        monkeypatch.setattr("main.self_improve._create_pr", lambda *args, **kwargs: None)

        def fail_if_called(*args, **kwargs):
            raise AssertionError("PRD stage should not rerun on planning resume")

        plan_calls = []
        exec_calls = []

        def fake_plan(**kwargs):
            plan_calls.append(kwargs)
            return {
                "quality_score": 9.0,
                "plan_path_json": str(tmp_path / "prd_output" / "exec_test.json"),
                "plan_path_md": str(tmp_path / "prd_output" / "exec_test.md"),
            }

        def fake_execution(**kwargs):
            exec_calls.append(kwargs)
            return {
                "overall_success": True,
                "story_status": "completed",
                "run_id": "run-456",
                "task_flow_ids": {"T-001": "task-flow-2"},
                "output_path": str(tmp_path / "exec_output" / "run-456"),
                "report_path": str(tmp_path / "exec_output" / "run-456" / "report.json"),
            }

        with patch("dialectic.prd_flow.DialecticFlow", side_effect=fail_if_called):
            with patch("planning.flow.run_user_story_planning", side_effect=fake_plan):
                with patch("execution.dialectic_execution.run_dialectic_execution", side_effect=fake_execution):
                    resumed = run_self_improve(resume_cycle_id="cycle-failed-plan")

        assert resumed.failure_reason == ""
        assert resumed.plan_generated is True
        assert resumed.execution_run_id == "run-456"
        assert plan_calls == [{
            "prd_path": str(tmp_path / "prd_output" / "PRD_test.json"),
            "user_story_ref": None,
            "vision_context": VisionContext.SELF,
        }]
        assert exec_calls == [{
            "plan_path": str(tmp_path / "prd_output" / "exec_test.json"),
            "vision_context": VisionContext.SELF,
            "resume_run_id": None,
        }]


class TestSelfImprovePrBody:
    def test_includes_artifact_lineage(self):
        report = IntrospectionReport(
            timestamp="2026-03-09T00:00:00Z",
            opportunities=[
                ImprovementOpportunity(
                    id="opp-1",
                    category="code_health",
                    title="Tighten lineage tracking",
                    description="Store exact artifact paths for review.",
                    evidence=["tests/test_self_improve_lineage.py"],
                    estimated_impact="high",
                )
            ],
            baseline_metrics={"prd_score": {"count": 5, "mean": 9.1}},
        )
        record = SelfImprovementRecord(
            cycle_id="cycle-1",
            timestamp="2026-03-09T00:00:00Z",
            prd_path_json="prd_output/PRD_test.json",
            prd_path_md="prd_output/PRD_test.md",
            plan_path_json="prd_output/exec_test.json",
            plan_path_md="prd_output/exec_test.md",
            execution_run_id="run-123",
            execution_output_path="exec_output/run-123",
            execution_report_path="exec_output/run-123/report.json",
        )

        body = _build_pr_body(report, report.opportunities, record)

        assert "### Artifacts" in body
        assert "PRD JSON: prd_output/PRD_test.json" in body
        assert "PRD flow ID:" in body
        assert "Plan JSON: prd_output/exec_test.json" in body
        assert "Execution report: exec_output/run-123/report.json" in body
