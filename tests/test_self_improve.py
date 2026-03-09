"""Tests for main.self_improve -- self-improvement orchestrator."""

import subprocess
import sys

import pytest

from dialectic.introspect import run_introspection
from dialectic.metrics import MetricRecord, MetricsStore, _reset_metrics_store
from dialectic.vision import VisionContext
from main.self_improve import (
    PROTECTED_PATHS,
    _create_pr,
    _metrics_stable,
    _pytest_command,
    _snapshot_tests,
    run_self_improve,
)
from schemas import SelfImprovementRecord


@pytest.fixture(autouse=True)
def _reset_singleton():
    _reset_metrics_store()
    yield
    _reset_metrics_store()


@pytest.fixture
def store(tmp_path):
    return MetricsStore(db_path=tmp_path / "test_self_improve.db")


class TestProtectedPaths:
    def test_self_vision_protected(self):
        assert "internal/SELF_VISION.md" in PROTECTED_PATHS

    def test_self_improve_protected(self):
        assert "src/main/self_improve.py" in PROTECTED_PATHS

    def test_metrics_protected(self):
        assert "src/dialectic/metrics.py" in PROTECTED_PATHS

    def test_introspect_protected(self):
        assert "src/dialectic/introspect.py" in PROTECTED_PATHS


class TestMetricsStable:
    def test_stable_when_no_regression(self, store):
        baseline = {"prd_score": {"count": 5, "mean": 9.0, "min": 8.0, "max": 10.0}}
        for _ in range(5):
            store.record(MetricRecord(metric_type="prd_score", value=9.0))
        stable, reason = _metrics_stable(store, baseline)
        assert stable
        assert "stable" in reason

    def test_detects_regression(self, store):
        baseline = {"prd_score": {"count": 5, "mean": 9.0, "min": 8.0, "max": 10.0}}
        for _ in range(5):
            store.record(MetricRecord(metric_type="prd_score", value=5.0))
        stable, reason = _metrics_stable(store, baseline)
        assert not stable
        assert "regressed" in reason

    def test_skips_insufficient_data(self, store):
        baseline = {"prd_score": {"count": 1, "mean": 9.0}}
        stable, _ = _metrics_stable(store, baseline)
        assert stable

    def test_empty_baseline(self, store):
        stable, _ = _metrics_stable(store, {})
        assert stable


class TestSnapshotTests:
    def test_prefers_uv_when_available(self, monkeypatch):
        monkeypatch.setattr(
            "main.self_improve.shutil.which",
            lambda name: "/usr/bin/uv" if name == "uv" else None,
        )
        assert _pytest_command() == ["uv", "run", "pytest", "--tb=short", "-q"]

    def test_falls_back_to_active_python_when_uv_missing(self, monkeypatch):
        monkeypatch.setattr("main.self_improve.shutil.which", lambda name: None)
        assert _pytest_command() == [sys.executable, "-m", "pytest", "--tb=short", "-q"]

    def test_returns_dict(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "main.self_improve._run_cmd",
            lambda cmd, cwd=None, timeout=120: subprocess.CompletedProcess(
                cmd, 0, stdout="10 passed\n", stderr=""
            ),
        )
        result = _snapshot_tests(tmp_path)
        assert result["passed"] is True
        assert result["returncode"] == 0

    def test_failing_tests(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "main.self_improve._run_cmd",
            lambda cmd, cwd=None, timeout=120: subprocess.CompletedProcess(
                cmd, 1, stdout="1 failed\n", stderr=""
            ),
        )
        result = _snapshot_tests(tmp_path)
        assert result["passed"] is False


class TestRunSelfImprove:
    def test_dry_run_no_changes(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True)
        vision.write_text("- [ ] Unfinished feature\n")

        monkeypatch.setattr(
            "main.self_improve.resolve_project_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            "main.self_improve.get_metrics_store", lambda: store
        )
        monkeypatch.setattr(
            "main.self_improve._git_worktree_clean", lambda cwd: (True, "clean")
        )
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr(
            "dialectic.introspect.get_vision_path", lambda ctx: vision
        )
        monkeypatch.setattr(
            "dialectic.introspect.resolve_project_root", lambda: tmp_path
        )

        record = run_self_improve(dry_run=True)
        assert record.failure_reason == "dry_run"
        assert record.opportunities_found >= 1
        assert not record.prd_generated

    def test_aborts_when_baseline_tests_fail(self, tmp_path, monkeypatch, store):
        monkeypatch.setattr(
            "main.self_improve.resolve_project_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            "main.self_improve.get_metrics_store", lambda: store
        )
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 1, "passed": False, "stdout_tail": "fail", "stderr_tail": ""},
        )

        record = run_self_improve()
        assert "Baseline tests" in record.failure_reason

    def test_aborts_when_no_opportunities(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True)
        vision.write_text("- [x] All done\n")

        monkeypatch.setattr(
            "main.self_improve.resolve_project_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            "main.self_improve.get_metrics_store", lambda: store
        )
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr(
            "dialectic.introspect.get_vision_path", lambda ctx: vision
        )
        monkeypatch.setattr(
            "dialectic.introspect.resolve_project_root", lambda: tmp_path
        )

        record = run_self_improve()
        assert "No improvement" in record.failure_reason

    def test_aborts_when_git_missing(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Need git preflight\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr("main.self_improve._git_worktree_clean", lambda cwd: (True, "clean"))
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.dialectic_prioritize", lambda opps, **kw: opps)
        monkeypatch.setattr(
            "main.self_improve.shutil.which",
            lambda name: None if name == "git" else "/usr/bin/uv",
        )

        record = run_self_improve(max_improvements=1)

        assert "Git is required" in record.failure_reason

    def test_uses_generated_prd_path_for_planning(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Improve artifact handoff\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr("main.self_improve._git_worktree_clean", lambda cwd: (True, "clean"))
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.dialectic_prioritize", lambda opps, **kw: opps)
        monkeypatch.setattr("main.self_improve._git_worktree_clean", lambda cwd: (True, "clean"))
        monkeypatch.setattr("main.self_improve._git_branch_create", lambda b, c: True)
        monkeypatch.setattr("main.self_improve._git_discard_branch", lambda b, c: None)
        monkeypatch.setattr("main.self_improve._create_pr", lambda *args, **kwargs: None)

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = str(tmp_path / "prd_output" / "PRD_test.json")

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": str(tmp_path / "prd_output" / "exec_test.json"),
        }
        mock_exec = {"overall_success": True, "story_status": "completed"}

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan) as mock_plan_run:
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(max_improvements=1)

        assert record.prd_generated is True
        mock_plan_run.assert_called_once_with(
            prd_path=str(tmp_path / "prd_output" / "PRD_test.json"),
            user_story_ref=None,
            vision_context=VisionContext.SELF,
        )

    def test_aborts_when_prd_export_path_missing(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Improve export tracking\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.dialectic_prioritize", lambda opps, **kw: opps)
        monkeypatch.setattr("main.self_improve._git_worktree_clean", lambda cwd: (True, "clean"))
        monkeypatch.setattr("main.self_improve._git_branch_create", lambda b, c: True)
        monkeypatch.setattr("main.self_improve._git_discard_branch", lambda b, c: None)

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = ""

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                record = run_self_improve(max_improvements=1)

        assert "did not produce an exported JSON artifact" in record.failure_reason


class TestSelfImprovementRecord:
    def test_schema_defaults(self):
        r = SelfImprovementRecord(
            cycle_id="test", timestamp="2026-01-01T00:00:00Z"
        )
        assert r.prd_generated is False
        assert r.pr_created is False
        assert r.branch_name == ""

    def test_token_fields(self):
        r = SelfImprovementRecord(
            cycle_id="t",
            timestamp="2026-01-01T00:00:00Z",
            total_tokens=50000,
            estimated_cost=0.125,
        )
        assert r.total_tokens == 50000
        assert r.estimated_cost == 0.125

    def test_token_fields_default_zero(self):
        r = SelfImprovementRecord(
            cycle_id="t", timestamp="2026-01-01T00:00:00Z"
        )
        assert r.total_tokens == 0
        assert r.estimated_cost == 0.0


class TestCreatePr:
    def test_returns_none_when_gh_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "main.self_improve.shutil.which",
            lambda name: None if name == "gh" else "/usr/bin/git",
        )
        assert _create_pr("branch", "title", "body", tmp_path) is None


class TestTokenBudgetIntegration:
    """Verify self_improve correctly wires HookScope and token tracking."""

    def _setup_introspection(self, tmp_path, monkeypatch, store):
        """Helper: setup mocks so introspection finds opportunities."""
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Unfinished feature A\n- [ ] Unfinished feature B\n")

        monkeypatch.setattr(
            "main.self_improve.resolve_project_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            "main.self_improve.get_metrics_store", lambda: store
        )
        monkeypatch.setattr(
            "main.self_improve._git_worktree_clean", lambda cwd: (True, "clean")
        )
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr(
            "dialectic.introspect.get_vision_path", lambda ctx: vision
        )
        monkeypatch.setattr(
            "dialectic.introspect.resolve_project_root", lambda: tmp_path
        )
        return vision

    def test_dry_run_no_hooks_registered(self, tmp_path, monkeypatch, store):
        from crewai.hooks import get_before_llm_call_hooks, clear_all_global_hooks
        clear_all_global_hooks()
        self._setup_introspection(tmp_path, monkeypatch, store)

        record = run_self_improve(dry_run=True)
        assert record.failure_reason == "dry_run"
        assert len(get_before_llm_call_hooks()) == 0

    def test_self_improve_aborts_on_budget_exceeded(self, tmp_path, monkeypatch, store):
        """With a budget of 1 token, any LLM-adjacent step should trigger abort."""
        self._setup_introspection(tmp_path, monkeypatch, store)

        monkeypatch.setenv("SELF_IMPROVE_TOKEN_BUDGET", "1")

        monkeypatch.setattr(
            "main.self_improve.dialectic_prioritize",
            lambda opps, **kw: opps,
        )
        monkeypatch.setattr(
            "main.self_improve._git_branch_create", lambda b, c: True
        )
        monkeypatch.setattr(
            "main.self_improve._git_discard_branch", lambda b, c: None
        )

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True

        def fake_kickoff(**kwargs):
            from dialectic.hooks import _get_active_scope
            scope = _get_active_scope()
            if scope:
                scope.tracker.add_input_tokens(100)
            return MagicMock()

        mock_flow.kickoff = fake_kickoff

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                record = run_self_improve(max_improvements=1)

        assert "Token budget exceeded" in record.failure_reason

    def test_record_contains_token_usage(self, tmp_path, monkeypatch, store):
        self._setup_introspection(tmp_path, monkeypatch, store)

        monkeypatch.setenv("SELF_IMPROVE_TOKEN_BUDGET", "10000000")

        monkeypatch.setattr(
            "main.self_improve.dialectic_prioritize",
            lambda opps, **kw: opps,
        )
        monkeypatch.setattr(
            "main.self_improve._git_branch_create", lambda b, c: True
        )
        monkeypatch.setattr(
            "main.self_improve._git_discard_branch", lambda b, c: None
        )

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_data = {}

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": "fake_plan.json",
        }

        mock_exec = {"overall_success": False, "story_status": "failed"}

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(max_improvements=1)

        assert isinstance(record.total_tokens, int)
        assert isinstance(record.estimated_cost, float)


class TestDialecticPrioritizationIntegration:
    """Verify self_improve calls dialectic_prioritize."""

    def test_self_improve_uses_dialectic_prioritization(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Unfinished feature\n")

        monkeypatch.setattr(
            "main.self_improve.resolve_project_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            "main.self_improve.get_metrics_store", lambda: store
        )
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr(
            "dialectic.introspect.get_vision_path", lambda ctx: vision
        )
        monkeypatch.setattr(
            "dialectic.introspect.resolve_project_root", lambda: tmp_path
        )

        prioritize_called = []

        def mock_prioritize(opps, **kwargs):
            prioritize_called.append(len(opps))
            return opps

        monkeypatch.setattr(
            "main.self_improve.dialectic_prioritize", mock_prioritize
        )
        monkeypatch.setattr(
            "main.self_improve._git_branch_create", lambda b, c: True
        )
        monkeypatch.setattr(
            "main.self_improve._git_discard_branch", lambda b, c: None
        )

        from unittest.mock import MagicMock, patch
        mock_flow = MagicMock()
        mock_flow.state.quality_score = 5.0
        mock_flow.state.consensus_reached = False

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                run_self_improve(max_improvements=1)

        assert len(prioritize_called) == 1
        assert prioritize_called[0] >= 1

    def test_fallback_when_prioritization_fails(self, tmp_path, monkeypatch, store):
        """When dialectic_prioritize raises, run_self_improve falls back to impact sort and continues."""
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Feature A\n- [ ] Feature B\n")

        monkeypatch.setattr(
            "main.self_improve.resolve_project_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            "main.self_improve.get_metrics_store", lambda: store
        )
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr(
            "dialectic.introspect.get_vision_path", lambda ctx: vision
        )
        monkeypatch.setattr(
            "dialectic.introspect.resolve_project_root", lambda: tmp_path
        )

        def failing_prioritize(opps, **kwargs):
            raise RuntimeError("prioritization failed")

        monkeypatch.setattr(
            "main.self_improve.dialectic_prioritize", failing_prioritize
        )
        monkeypatch.setattr(
            "main.self_improve._git_branch_create", lambda b, c: True
        )
        monkeypatch.setattr(
            "main.self_improve._git_discard_branch", lambda b, c: None
        )

        from unittest.mock import MagicMock, patch
        mock_flow = MagicMock()
        mock_flow.state.quality_score = 5.0
        mock_flow.state.consensus_reached = False

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                record = run_self_improve(dry_run=False, max_improvements=1)

        assert record.opportunities_attempted >= 1
        assert record.failure_reason != ""
