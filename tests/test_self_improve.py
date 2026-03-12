"""Tests for main.self_improve -- self-improvement orchestrator."""

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=redefined-outer-name,import-outside-toplevel,unused-argument
# pylint: disable=too-few-public-methods,line-too-long,too-many-lines,duplicate-code

import subprocess
import sys

import pytest

from dialectic.metrics import MetricRecord, MetricsStore, _reset_metrics_store
from dialectic.vision import VisionContext
from main.pr_builder import create_pr
from main.self_improve import (
    PROTECTED_PATHS,
    _create_pr,
    _list_resumable_cycles,
    _metrics_stable,
    _pytest_command,
    _self_improve_test_timeout,
    _snapshot_tests,
    _summarize_resume_state,
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
    def test_uses_configured_self_improve_timeout(self, tmp_path, monkeypatch):
        seen = {}

        def fake_run(cmd, cwd=None, timeout=120):
            seen["timeout"] = timeout
            return subprocess.CompletedProcess(cmd, 0, stdout="10 passed\n", stderr="")

        monkeypatch.setenv("SELF_IMPROVE_TEST_TIMEOUT", "1234")
        monkeypatch.setattr("main.self_improve._run_cmd", fake_run)

        result = _snapshot_tests(tmp_path)

        assert result["passed"] is True
        assert result["timeout_seconds"] == 1234
        assert seen["timeout"] == 1234

    def test_invalid_self_improve_timeout_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("SELF_IMPROVE_TEST_TIMEOUT", "not-a-number")

        assert _self_improve_test_timeout() == 1800

    def test_prefers_uv_when_available(self, monkeypatch):
        monkeypatch.setattr(
            "main.self_improve.shutil.which",
            lambda name: "/usr/bin/uv" if name == "uv" else None,
        )
        assert _pytest_command() == [
            "uv", "run", "pytest", "--tb=short", "-q", "--reruns", "1"
        ]

    def test_falls_back_to_active_python_when_uv_missing(self, monkeypatch):
        monkeypatch.setattr("main.self_improve.shutil.which", lambda name: None)
        assert _pytest_command() == [
            sys.executable, "-m", "pytest", "--tb=short", "-q", "--reruns", "1"
        ]

    def test_includes_single_rerun_for_flaky_llm_tests(self, monkeypatch):
        monkeypatch.setattr(
            "main.self_improve.shutil.which",
            lambda name: "/usr/bin/uv" if name == "uv" else None,
        )

        assert _pytest_command().count("--reruns") == 1
        assert _pytest_command()[-1] == "1"

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

    def test_timeout_returns_diagnostics(self, tmp_path, monkeypatch):
        def fake_run(cmd, cwd=None, timeout=120):
            raise subprocess.TimeoutExpired(
                cmd=cmd,
                timeout=timeout,
                output="still running\n",
                stderr="hung test\n",
            )

        monkeypatch.setattr("main.self_improve._run_cmd", fake_run)

        result = _snapshot_tests(tmp_path, timeout=42)

        assert result == {
            "returncode": -1,
            "passed": False,
            "timed_out": True,
            "timeout_seconds": 42,
            "command": _pytest_command(),
            "stdout_tail": "still running\n",
            "stderr_tail": "hung test\n",
        }


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

    def test_baseline_failure_prints_pytest_details(self, tmp_path, monkeypatch, store, capsys):
        monkeypatch.setattr(
            "main.self_improve.resolve_project_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            "main.self_improve.get_metrics_store", lambda: store
        )
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {
                "returncode": 2,
                "passed": False,
                "timed_out": False,
                "timeout_seconds": 900,
                "command": ["uv", "run", "pytest", "--tb=short", "-q", "--reruns", "1"],
                "stdout_tail": "collected 10 items\n",
                "stderr_tail": "E   AssertionError: boom\n",
            },
        )

        record = run_self_improve()
        out = capsys.readouterr().out

        assert "Baseline tests" in record.failure_reason
        assert "Pytest exited with code 2" in out
        assert "stdout tail:" in out
        assert "stderr tail:" in out
        assert "AssertionError: boom" in out

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
        mock_exec = {
            "overall_success": True,
            "story_status": "completed",
            "run_id": "run-commit-test",
            "task_flow_ids": {"T-001": "task-flow-commit-test"},
            "output_path": str(tmp_path / "exec_output" / "run-commit-test"),
            "report_path": str(tmp_path / "exec_output" / "run-commit-test" / "report.json"),
        }

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

    def test_creates_commit_before_pr(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Improve PR handoff\n")

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
        monkeypatch.setattr("main.self_improve._git_branch_create", lambda b, c: True)
        monkeypatch.setattr("main.self_improve._git_discard_branch", lambda b, c: None)

        commit_calls: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "main.self_improve._git_commit_all",
            lambda cwd, message: (commit_calls.append((str(cwd), message)) or True, "created commit"),
        )
        monkeypatch.setattr(
            "main.self_improve._git_has_commits_ahead",
            lambda cwd, base_branch="main": (True, f"1 commit ahead of {base_branch}"),
        )
        monkeypatch.setattr("main.self_improve._create_pr", lambda *args, **kwargs: "https://example/pr/1")

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = str(tmp_path / "prd_output" / "PRD_test.json")

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": str(tmp_path / "prd_output" / "exec_test.json"),
        }
        mock_exec = {
            "overall_success": True,
            "story_status": "completed",
            "run_id": "run-no-commit-test",
            "task_flow_ids": {"T-001": "task-flow-no-commit-test"},
            "output_path": str(tmp_path / "exec_output" / "run-no-commit-test"),
            "report_path": str(tmp_path / "exec_output" / "run-no-commit-test" / "report.json"),
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(max_improvements=1)

        assert record.pr_created is True
        assert commit_calls
        assert commit_calls[0][0] == str(tmp_path)
        assert commit_calls[0][1].startswith("chore(self-improve): apply cycle ")

    def test_skips_pr_when_no_commits_ahead(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Improve no-op PR handling\n")

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
        monkeypatch.setattr("main.self_improve._git_branch_create", lambda b, c: True)
        monkeypatch.setattr("main.self_improve._git_discard_branch", lambda b, c: None)
        monkeypatch.setattr(
            "main.self_improve._git_commit_all",
            lambda cwd, message: (False, "nothing to commit"),
        )
        monkeypatch.setattr(
            "main.self_improve._git_has_commits_ahead",
            lambda cwd, base_branch="main": (False, f"no commits ahead of {base_branch}"),
        )

        pr_attempted = {"value": False}

        def fake_create_pr(*_args, **_kwargs):
            pr_attempted["value"] = True
            return "https://example/pr/1"

        monkeypatch.setattr("main.self_improve._create_pr", fake_create_pr)

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = str(tmp_path / "prd_output" / "PRD_test.json")

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": str(tmp_path / "prd_output" / "exec_test.json"),
        }
        mock_exec = {
            "overall_success": True,
            "story_status": "completed",
            "run_id": "run-no-commit-test",
            "task_flow_ids": {"T-001": "task-flow-no-commit-test"},
            "output_path": str(tmp_path / "exec_output" / "run-no-commit-test"),
            "report_path": str(tmp_path / "exec_output" / "run-no-commit-test" / "report.json"),
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(max_improvements=1)

        assert record.pr_created is False
        assert "No committable source changes" in record.failure_reason
        assert pr_attempted["value"] is False

    def test_resume_prints_last_failure_next_stage_and_reused_artifacts(
        self,
        tmp_path,
        monkeypatch,
        store,
        capsys,
    ):
        from main.self_improve import _save_self_improve_record
        from schemas import ImprovementOpportunity

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr("main.self_improve._create_pr", lambda *args, **kwargs: None)

        record = SelfImprovementRecord(
            cycle_id="cycle-summary",
            timestamp="2026-03-10T00:00:00Z",
            baseline_metrics={"prd_score": {"count": 0, "mean": 0}},
            selected_opportunities=[
                ImprovementOpportunity(
                    id="opp-1",
                    category="code_health",
                    title="Recover failed execution",
                    description="Resume from execution.",
                    evidence=["exec_output/run-123/checkpoint.json"],
                    estimated_impact="high",
                )
            ],
            opportunities_found=1,
            opportunities_attempted=1,
            prd_generated=True,
            plan_generated=True,
            execution_attempted=True,
            prd_path_json=str(tmp_path / "prd_output" / "PRD_test.json"),
            plan_path_json=str(tmp_path / "prd_output" / "exec_test.json"),
            execution_run_id="run-123",
            failure_reason="Execution failed: failed",
        )
        _save_self_improve_record(tmp_path, record)

        monkeypatch.setattr(
            "execution.dialectic_execution.run_dialectic_execution",
            lambda **kwargs: {
                "overall_success": True,
                "story_status": "completed",
                "run_id": "run-123",
                "task_flow_ids": {},
                "output_path": str(tmp_path / "exec_output" / "run-123"),
                "report_path": str(tmp_path / "exec_output" / "run-123" / "report.json"),
            },
        )

        run_self_improve(resume_cycle_id="cycle-summary")
        out = capsys.readouterr().out

        assert "[resume] Last failure: Execution failed: failed" in out
        assert "[resume] Next stage: execution" in out
        assert f"PRD: {tmp_path / 'prd_output' / 'PRD_test.json'}" in out
        assert "Execution run: run-123" in out

    def test_resume_switches_to_recorded_branch_when_current_branch_drifted(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        from main.self_improve import _save_self_improve_record
        from schemas import ImprovementOpportunity

        git_dir = tmp_path / ".git"
        git_dir.write_text("gitdir: /fake/worktree\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr(
            "main.self_improve._git_commit_all",
            lambda cwd, message: (False, "nothing to commit"),
        )
        monkeypatch.setattr(
            "main.self_improve._git_has_commits_ahead",
            lambda cwd, base_branch="main": (True, f"1 commit ahead of {base_branch}"),
        )
        monkeypatch.setattr("main.self_improve._create_pr", lambda *args, **kwargs: None)

        switched = []
        monkeypatch.setattr(
            "main.self_improve._git_current_branch",
            lambda cwd: "self-improve/other-cycle",
        )
        monkeypatch.setattr(
            "main.self_improve._git_checkout_branch",
            lambda branch, cwd: (switched.append((branch, str(cwd))) or True, f"switched to {branch}"),
        )

        record = SelfImprovementRecord(
            cycle_id="cycle-switch",
            timestamp="2026-03-10T00:00:00Z",
            baseline_metrics={"prd_score": {"count": 0, "mean": 0}},
            selected_opportunities=[
                ImprovementOpportunity(
                    id="opp-1",
                    category="code_health",
                    title="Resume on the correct branch",
                    description="Ensure resume reattaches to the recorded git branch.",
                    evidence=[".dialectic/self_improve/cycle-switch.json"],
                    estimated_impact="high",
                )
            ],
            opportunities_found=1,
            opportunities_attempted=1,
            prd_generated=True,
            plan_generated=True,
            execution_attempted=True,
            branch_name="self-improve/cycle-switch",
            prd_path_json=str(tmp_path / "prd_output" / "PRD_test.json"),
            plan_path_json=str(tmp_path / "prd_output" / "exec_test.json"),
            execution_run_id="run-123",
            execution_output_path=str(tmp_path / "exec_output" / "run-123"),
            execution_report_path=str(tmp_path / "exec_output" / "run-123" / "report.json"),
            failure_reason="PR creation failed: drifted branch",
        )
        _save_self_improve_record(tmp_path, record)

        resumed = run_self_improve(resume_cycle_id="cycle-switch")

        assert resumed.failure_reason == ""
        assert switched == [("self-improve/cycle-switch", str(tmp_path))]

    def test_resume_recreates_missing_recorded_branch_from_current_self_improve_head(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        from main.self_improve import _save_self_improve_record
        from schemas import ImprovementOpportunity

        git_dir = tmp_path / ".git"
        git_dir.write_text("gitdir: /fake/worktree\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr(
            "main.self_improve._git_commit_all",
            lambda cwd, message: (False, "nothing to commit"),
        )
        monkeypatch.setattr(
            "main.self_improve._git_has_commits_ahead",
            lambda cwd, base_branch="main": (True, f"1 commit ahead of {base_branch}"),
        )
        monkeypatch.setattr("main.self_improve._create_pr", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            "main.self_improve._git_current_branch",
            lambda cwd: "self-improve/other-cycle",
        )
        monkeypatch.setattr(
            "main.self_improve._git_checkout_branch",
            lambda branch, cwd: (False, f"pathspec '{branch}' did not match any file(s) known to git"),
        )

        recreated = []
        monkeypatch.setattr(
            "main.self_improve._git_branch_create_from_head",
            lambda branch, cwd: (recreated.append((branch, str(cwd))) or True, f"created {branch}"),
        )

        record = SelfImprovementRecord(
            cycle_id="cycle-recreate",
            timestamp="2026-03-10T00:00:00Z",
            baseline_metrics={"prd_score": {"count": 0, "mean": 0}},
            selected_opportunities=[
                ImprovementOpportunity(
                    id="opp-1",
                    category="code_health",
                    title="Recreate the missing branch",
                    description="Resume should restore the recorded branch from the current self-improve HEAD.",
                    evidence=[".dialectic/self_improve/cycle-recreate.json"],
                    estimated_impact="high",
                )
            ],
            opportunities_found=1,
            opportunities_attempted=1,
            prd_generated=True,
            plan_generated=True,
            execution_attempted=True,
            branch_name="self-improve/cycle-recreate",
            prd_path_json=str(tmp_path / "prd_output" / "PRD_test.json"),
            plan_path_json=str(tmp_path / "prd_output" / "exec_test.json"),
            execution_run_id="run-123",
            execution_output_path=str(tmp_path / "exec_output" / "run-123"),
            execution_report_path=str(tmp_path / "exec_output" / "run-123" / "report.json"),
            failure_reason="PR creation failed: missing branch",
        )
        _save_self_improve_record(tmp_path, record)

        resumed = run_self_improve(resume_cycle_id="cycle-recreate")

        assert resumed.failure_reason == ""
        assert recreated == [("self-improve/cycle-recreate", str(tmp_path))]


class TestResumeSummary:
    def test_prefers_execution_after_failed_execution(self):
        summary = _summarize_resume_state(
            SelfImprovementRecord(
                cycle_id="c1",
                timestamp="2026-03-10T00:00:00Z",
                prd_generated=True,
                plan_generated=True,
                execution_attempted=True,
                prd_path_json="prd.json",
                plan_path_json="plan.json",
                execution_run_id="run-1",
            ),
            "Execution failed: failed",
        )

        assert summary["next_stage"] == "execution"

    def test_prefers_planning_when_prd_exists_but_plan_missing(self):
        summary = _summarize_resume_state(
            SelfImprovementRecord(
                cycle_id="c2",
                timestamp="2026-03-10T00:00:00Z",
                prd_generated=True,
                prd_path_json="prd.json",
            ),
            "Plan quality too low: 6.0",
        )

        assert summary["next_stage"] == "planning"


class TestResumableCycles:
    def test_lists_saved_cycles_in_newest_first_order(self, tmp_path):
        from main.self_improve import _save_self_improve_record

        older = SelfImprovementRecord(
            cycle_id="cycle-old",
            timestamp="2026-03-10T00:00:00Z",
            prd_generated=True,
            failure_reason="Plan quality too low: 6.0",
        )
        newer = SelfImprovementRecord(
            cycle_id="cycle-new",
            timestamp="2026-03-10T01:00:00Z",
            prd_generated=True,
            plan_generated=True,
            execution_attempted=True,
            execution_run_id="run-123",
            failure_reason="Execution failed: failed",
        )
        _save_self_improve_record(tmp_path, older)
        _save_self_improve_record(tmp_path, newer)

        rows = _list_resumable_cycles(tmp_path)

        assert [row["cycle_id"] for row in rows] == ["cycle-new", "cycle-old"]
        assert rows[0]["next_stage"] == "execution"
        assert rows[1]["next_stage"] == "planning"


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

    def test_pushes_branch_before_creating_pr(self, tmp_path):
        commands = []

        def fake_run(cmd, cwd=None, timeout=120):
            commands.append(cmd)
            if cmd[:3] == ["git", "push", "-u"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="pushed\n", stderr="")
            if cmd[:3] == ["gh", "pr", "create"]:
                return subprocess.CompletedProcess(cmd, 0, stdout="https://example/pr/123\n", stderr="")
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="unexpected command")

        pr_url = create_pr(
            "self-improve/test-cycle",
            "title",
            "body",
            tmp_path,
            command_available_fn=lambda command: True,
            run_cmd_fn=fake_run,
            logger=type("Logger", (), {"warning": lambda self, msg, *args: None})(),
        )

        assert pr_url == "https://example/pr/123"
        assert commands == [
            ["git", "push", "-u", "origin", "self-improve/test-cycle"],
            ["gh", "pr", "create", "--title", "title", "--body", "body", "--head", "self-improve/test-cycle"],
        ]

    def test_returns_none_when_push_fails(self, tmp_path):
        commands = []
        warnings = []

        class Logger:
            def warning(self, msg, *args):
                warnings.append(msg % args if args else msg)

        def fake_run(cmd, cwd=None, timeout=120):
            commands.append(cmd)
            if cmd[:3] == ["git", "push", "-u"]:
                return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="push rejected")
            return subprocess.CompletedProcess(cmd, 0, stdout="https://example/pr/123\n", stderr="")

        pr_url = create_pr(
            "self-improve/test-cycle",
            "title",
            "body",
            tmp_path,
            command_available_fn=lambda command: True,
            run_cmd_fn=fake_run,
            logger=Logger(),
        )

        assert pr_url is None
        assert commands == [["git", "push", "-u", "origin", "self-improve/test-cycle"]]
        assert warnings == ["PR branch push failed: push rejected"]


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
