"""Focused tests for self-improve artifact lineage and stage validation."""

from unittest.mock import MagicMock, patch

import pytest

from dialectic.metrics import MetricsStore, _reset_metrics_store
from dialectic.vision import VisionContext
from main.self_improve import _build_pr_body, run_self_improve
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
            "report_path": str(tmp_path / "exec_output" / "run-123" / "report.json"),
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(max_improvements=1)

        assert record.prd_path_json == mock_flow.state.prd_path_json
        assert record.prd_path_md == mock_flow.state.prd_path_md
        assert record.plan_path_json == mock_plan["plan_path_json"]
        assert record.plan_path_md == mock_plan["plan_path_md"]
        assert record.execution_run_id == mock_exec["run_id"]
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
        assert "Plan JSON: prd_output/exec_test.json" in body
        assert "Execution report: exec_output/run-123/report.json" in body
