"""Tests for main.self_improve -- self-improvement orchestrator."""

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=redefined-outer-name,import-outside-toplevel,unused-argument
# pylint: disable=too-few-public-methods,line-too-long,too-many-lines,duplicate-code
# pylint: disable=too-many-public-methods,too-many-locals

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest

from dialectic.app_logging import configure_application_logging, get_logging_config, shutdown_application_logging
from dialectic.crew_verbose_config import get_output_log_file
from dialectic.metrics import MetricRecord, MetricsStore, _reset_metrics_store
from dialectic.vision import VisionContext
from src.main.self_improve.internal.orchestrator import (
    _self_improve_execution_retries,
    _simulation_runtime_environment,
    _simulation_runtime_root,
)
from src.main.self_improve.pr_builder import create_pr
from src.main.self_improve.persistence import load_self_improve_record
from src.main.self_improve import (
    PROTECTED_PATHS,
    SIMULATION_BRANCH_NAME,
    _create_pr,
    _is_transient_llm_error,
    _list_resumable_cycles,
    _metrics_stable,
    _pytest_command,
    _run_with_transient_llm_retries,
    _self_improve_llm_stage_retries,
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
        assert "src/main/self_improve/orchestrator.py" in PROTECTED_PATHS

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

    def test_invalid_llm_stage_retry_budget_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("SELF_IMPROVE_LLM_STAGE_RETRIES", "not-a-number")

        assert _self_improve_llm_stage_retries() == 2

    def test_invalid_execution_retry_budget_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("SELF_IMPROVE_EXECUTION_RETRIES", "not-a-number")

        assert _self_improve_execution_retries() == 1

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
    def test_simulation_runtime_environment_persists_and_restores_logging(
        self,
        tmp_path,
        monkeypatch,
    ):
        cycle_id = "cycle-123"
        original_log_dir = tmp_path / "logs"

        monkeypatch.setenv("DIALECTIC_LOG_DIR", str(original_log_dir))
        monkeypatch.setenv("CREWAI_VERBOSE", "true")
        monkeypatch.delenv("CREWAI_OUTPUT_LOG_FILE", raising=False)

        shutdown_application_logging()
        configure_application_logging(force=True)

        runtime_root = _simulation_runtime_root(tmp_path, cycle_id)
        try:
            with _simulation_runtime_environment(tmp_path, cycle_id) as active_root:
                assert active_root == runtime_root
                assert active_root.exists()
                assert os.getenv("DIALECTIC_RUNTIME_ROOT") == str(runtime_root)
                assert get_logging_config().log_dir == runtime_root / "logs"
                assert get_output_log_file() == (
                    runtime_root / "logs" / "crewai_verbose.log"
                ).as_posix()

            assert os.getenv("DIALECTIC_RUNTIME_ROOT") is None
            assert get_logging_config().log_dir == original_log_dir
        finally:
            shutdown_application_logging()

    def test_simulation_runtime_environment_preserves_explicit_crewai_logfile(
        self,
        tmp_path,
        monkeypatch,
    ):
        explicit_log = tmp_path / "explicit-crewai.log"

        monkeypatch.setenv("CREWAI_VERBOSE", "true")
        monkeypatch.setenv("CREWAI_OUTPUT_LOG_FILE", str(explicit_log))

        with _simulation_runtime_environment(tmp_path, "cycle-explicit-log"):
            assert get_output_log_file() == explicit_log.as_posix()

    def test_rejects_more_than_one_opportunity(self):
        with pytest.raises(ValueError, match="exactly one opportunity"):
            run_self_improve(max_improvements=2)

    def test_rejects_resume_during_simulation(self):
        with pytest.raises(ValueError, match="does not support --resume"):
            run_self_improve(simulate=True, resume_cycle_id="cycle-123")

    def test_persists_resumable_state_when_prioritization_is_interrupted(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        from schemas import ImprovementOpportunity, IntrospectionReport

        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Preserve interrupted self-improve cycles\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr("main.self_improve._run_git_preflight", lambda *args, **kwargs: None)
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve._git_branch_create", lambda branch, cwd: True)
        monkeypatch.setattr("main.self_improve._git_discard_branch", lambda branch, cwd: None)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )

        opportunity = ImprovementOpportunity(
            id="vision-gap-1",
            category="code_health",
            title="Stabilize self-improve interruption handling",
            description="Persist resumable cycle state when prioritization is interrupted.",
            evidence=["internal/ROADMAP.md"],
            estimated_impact="high",
        )
        report = IntrospectionReport(
            timestamp="2026-03-16T00:00:00+00:00",
            opportunities=[opportunity],
            baseline_metrics={},
        )

        monkeypatch.setattr("main.self_improve.run_introspection", lambda **kwargs: report)

        def interrupt_prioritization(opps, **kwargs):
            del opps, kwargs
            raise KeyboardInterrupt()

        monkeypatch.setattr(
            "main.self_improve.dialectic_prioritize",
            interrupt_prioritization,
        )

        with pytest.raises(KeyboardInterrupt):
            run_self_improve()

        resumable = _list_resumable_cycles(tmp_path)
        assert len(resumable) == 1
        cycle_id = resumable[0]["cycle_id"]
        record = load_self_improve_record(tmp_path, cycle_id)

        assert record.failure_reason == "Interrupted during prioritization"
        assert record.selected_opportunities == [opportunity]
        assert record.opportunities_attempted == 1
        resume_summary = _summarize_resume_state(record, record.failure_reason)
        assert resume_summary["next_stage"] == "PRD generation"

    def test_enables_shutdown_noise_suppression_when_interrupted(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        from schemas import ImprovementOpportunity, IntrospectionReport

        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Suppress shutdown noise on interrupt\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr("main.self_improve._run_git_preflight", lambda *args, **kwargs: None)
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve._git_branch_create", lambda branch, cwd: True)
        monkeypatch.setattr("main.self_improve._git_discard_branch", lambda branch, cwd: None)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )

        opportunity = ImprovementOpportunity(
            id="vision-gap-2",
            category="code_health",
            title="Suppress shutdown noise",
            description="Enable known shutdown-noise suppression on user interrupt.",
            evidence=["internal/ROADMAP.md"],
            estimated_impact="high",
        )
        report = IntrospectionReport(
            timestamp="2026-03-16T00:00:00+00:00",
            opportunities=[opportunity],
            baseline_metrics={},
        )

        monkeypatch.setattr("main.self_improve.run_introspection", lambda **kwargs: report)

        suppression_calls: list[str] = []
        monkeypatch.setattr(
            "main.self_improve.enable_shutdown_noise_suppression",
            lambda: suppression_calls.append("enabled"),
        )

        def interrupt_prioritization(opps, **kwargs):
            del opps, kwargs
            raise KeyboardInterrupt()

        monkeypatch.setattr(
            "main.self_improve.dialectic_prioritize",
            interrupt_prioritization,
        )

        with pytest.raises(KeyboardInterrupt):
            run_self_improve()

        assert suppression_calls == ["enabled"]

    def test_retries_transient_llm_timeout_during_prd_generation(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Retry transient provider failures\n")

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
        monkeypatch.setattr("main.self_improve.time.sleep", lambda seconds: None)
        monkeypatch.setattr(
            "main.self_improve._git_commit_all",
            lambda cwd, message: (False, "nothing to commit"),
        )
        monkeypatch.setattr(
            "main.self_improve._git_has_commits_ahead",
            lambda cwd, base_branch="main": (False, f"no commits ahead of {base_branch}"),
        )

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.state.quality_score = 8.5
        mock_flow.state.consensus_reached = False
        mock_flow.state.prd_path_json = str(tmp_path / "prd_output" / "PRD_retry.json")
        mock_flow.state.prd_path_md = str(tmp_path / "prd_output" / "PRD_retry.md")

        attempts = {"count": 0}

        def fake_kickoff(*, inputs):
            del inputs
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise RuntimeError("Failed to connect to OpenAI API: Request timed out.")

        mock_flow.kickoff.side_effect = fake_kickoff

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": str(tmp_path / "prd_output" / "exec_retry.json"),
            "plan_path_md": str(tmp_path / "prd_output" / "exec_retry.md"),
        }
        mock_exec = {
            "overall_success": True,
            "story_status": "completed",
            "run_id": "run-retry-prd",
            "task_flow_ids": {"T-001": "task-flow-retry-prd"},
            "output_path": str(tmp_path / "exec_output" / "run-retry-prd"),
            "report_path": str(tmp_path / "exec_output" / "run-retry-prd" / "report.json"),
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(max_improvements=1)

        assert attempts["count"] == 2
        assert record.prd_generated is True
        assert record.plan_generated is True
        assert "Request timed out" not in record.failure_reason

    def test_skip_baseline_tests_skips_baseline_in_simulation(
        self,
        tmp_path,
        monkeypatch,
        store,
        capsys,
    ):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Skip baseline tests in simulation\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr("main.self_improve._run_git_preflight", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            "dialectic.introspect.get_vision_path",
            lambda ctx: vision,
        )
        monkeypatch.setattr(
            "dialectic.introspect.resolve_project_root",
            lambda: tmp_path,
        )
        monkeypatch.setattr("main.self_improve.dialectic_prioritize", lambda opps, **kw: opps)
        monkeypatch.setattr(
            "main.self_improve._prepare_simulation_branch",
            lambda cwd: (True, SIMULATION_BRANCH_NAME),
        )
        monkeypatch.setattr("main.self_improve._cleanup_simulation_branch", lambda cwd: None)
        monkeypatch.setattr(
            "main.self_improve.run_quality_gate",
            lambda cwd: type("QualityResult", (), {"passed": True, "summary": "ok"})(),
        )
        monkeypatch.setattr(
            "main.self_improve.validate_code_structure",
            lambda cwd, **kwargs: type(
                "StructureResult",
                (),
                {"passed": True, "summary": "ok", "violations": []},
            )(),
        )
        monkeypatch.setattr("main.self_improve._metrics_stable", lambda *args, **kwargs: (True, "stable"))
        monkeypatch.setattr(
            "main.self_improve._git_commit_all",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("simulate should not commit")),
        )

        snapshot_calls: list[str] = []

        def fake_snapshot(_project_root, timeout=None):
            del timeout
            snapshot_calls.append("called")
            return {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""}

        monkeypatch.setattr("main.self_improve._snapshot_tests", fake_snapshot)

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.flow_id = "flow-sim-skip-baseline"
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = str(tmp_path / "runtime" / "prd.json")
        mock_flow.state.prd_path_md = str(tmp_path / "runtime" / "prd.md")

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": str(tmp_path / "runtime" / "plan.json"),
            "plan_path_md": str(tmp_path / "runtime" / "plan.md"),
        }
        mock_exec = {
            "overall_success": True,
            "story_status": "completed",
            "run_id": "sim-run-skip-baseline",
            "task_flow_ids": {"T-001": "task-flow-sim-skip-baseline"},
            "output_path": str(tmp_path / "runtime" / "exec"),
            "report_path": str(tmp_path / "runtime" / "exec" / "report.json"),
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(
                            simulate=True,
                            skip_baseline_tests=True,
                        )

        out = capsys.readouterr().out

        assert record.failure_reason == "simulated"
        assert snapshot_calls == ["called"]
        assert "[1/6] Running baseline tests..." not in out
        assert "--skip-baseline-tests was requested" in out

    def test_next_roadmap_item_skips_dialectic_prioritization(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] First roadmap item\n- [ ] Second roadmap item\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr(
            "main.self_improve.dialectic_prioritize",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("--next-roadmap-item should bypass prioritization")
            ),
        )
        monkeypatch.setattr("main.self_improve._git_worktree_clean", lambda cwd: (True, "clean"))
        monkeypatch.setattr("main.self_improve._git_branch_create", lambda b, c: True)
        monkeypatch.setattr("main.self_improve._git_discard_branch", lambda b, c: None)

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.state.quality_score = 5.0
        mock_flow.state.consensus_reached = False

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                record = run_self_improve(max_improvements=1, next_roadmap_item=True)

        assert record.selected_opportunities
        assert "First roadmap item" in record.selected_opportunities[0].title

    def test_artifact_prd_path_starts_at_planning(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        artifact_path = tmp_path / "input_prd.json"
        artifact_path.write_text(
            json.dumps(
                {
                    "feature_name": "Shortcut PRD",
                    "user_stories": [{"id": "US-001", "title": "Shortcut story"}],
                }
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve.run_introspection",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("PRD shortcut should not run introspection")
            ),
        )
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr("main.self_improve._git_worktree_clean", lambda cwd: (True, "clean"))
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

        plan_calls: list[str] = []

        def fake_plan(*, prd_path, user_story_ref, vision_context):
            del user_story_ref, vision_context
            plan_calls.append(prd_path)
            return {
                "quality_score": 9.0,
                "plan_path_json": str(tmp_path / "prd_output" / "exec_shortcut.json"),
                "plan_path_md": str(tmp_path / "prd_output" / "exec_shortcut.md"),
            }

        exec_calls: list[str] = []

        def fake_exec(*, plan_path, vision_context, resume_run_id):
            del vision_context, resume_run_id
            exec_calls.append(plan_path)
            return {
                "overall_success": True,
                "story_status": "completed",
                "run_id": "run-shortcut-prd",
                "task_flow_ids": {"T-001": "task-flow-shortcut-prd"},
                "output_path": str(tmp_path / "exec_output" / "run-shortcut-prd"),
                "report_path": str(tmp_path / "exec_output" / "run-shortcut-prd" / "report.json"),
            }

        from unittest.mock import patch

        with patch("planning.flow.run_user_story_planning", side_effect=fake_plan):
            with patch("execution.dialectic_execution.run_dialectic_execution", side_effect=fake_exec):
                record = run_self_improve(max_improvements=1, artifact_path=str(artifact_path))

        assert plan_calls == [str(artifact_path)]
        assert exec_calls == [str(tmp_path / "prd_output" / "exec_shortcut.json")]
        assert record.prd_generated is True
        assert record.plan_generated is True

    def test_artifact_plan_path_starts_at_execution(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        artifact_path = tmp_path / "input_plan.json"
        artifact_path.write_text(
            json.dumps(
                {
                    "user_story_id": "US-001",
                    "tasks": [{"id": "T-001", "title": "Implement shortcut"}],
                }
            ),
            encoding="utf-8",
        )

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve.run_introspection",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("Plan shortcut should not run introspection")
            ),
        )
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr("main.self_improve._git_worktree_clean", lambda cwd: (True, "clean"))
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

        from unittest.mock import patch

        with patch(
            "planning.flow.run_user_story_planning",
            side_effect=AssertionError("Plan shortcut should bypass planning"),
        ):
            with patch(
                "execution.dialectic_execution.run_dialectic_execution",
                return_value={
                    "overall_success": True,
                    "story_status": "completed",
                    "run_id": "run-shortcut-plan",
                    "task_flow_ids": {"T-001": "task-flow-shortcut-plan"},
                    "output_path": str(tmp_path / "exec_output" / "run-shortcut-plan"),
                    "report_path": str(tmp_path / "exec_output" / "run-shortcut-plan" / "report.json"),
                },
            ) as mock_exec:
                record = run_self_improve(max_improvements=1, artifact_path=str(artifact_path))

        mock_exec.assert_called_once_with(
            plan_path=str(artifact_path),
            vision_context=VisionContext.SELF,
            resume_run_id=None,
        )
        assert record.plan_generated is True
        assert record.execution_attempted is True

    def test_skip_baseline_tests_skips_metrics_validation(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Skip metrics without baseline\n")

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
        monkeypatch.setattr(
            "main.self_improve._metrics_stable",
            lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("metrics validation should be skipped without a baseline")
            ),
        )
        monkeypatch.setattr(
            "main.self_improve._git_commit_all",
            lambda cwd, message: (False, "nothing to commit"),
        )
        monkeypatch.setattr(
            "main.self_improve._git_has_commits_ahead",
            lambda cwd, base_branch="main": (False, f"no commits ahead of {base_branch}"),
        )

        from unittest.mock import MagicMock, patch

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
            "run_id": "run-skip-metrics",
            "task_flow_ids": {"T-001": "task-flow-skip-metrics"},
            "output_path": str(tmp_path / "exec_output" / "run-skip-metrics"),
            "report_path": str(tmp_path / "exec_output" / "run-skip-metrics" / "report.json"),
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(max_improvements=1, skip_baseline_tests=True)

        assert record.tests_passed is True

    def test_simulation_prints_summary_report(
        self,
        tmp_path,
        monkeypatch,
        store,
        capsys,
    ):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Report simulation artifacts\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr("main.self_improve._run_git_preflight", lambda *args, **kwargs: None)
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.dialectic_prioritize", lambda opps, **kw: opps)
        monkeypatch.setattr(
            "main.self_improve._prepare_simulation_branch",
            lambda cwd: (True, SIMULATION_BRANCH_NAME),
        )
        monkeypatch.setattr("main.self_improve._cleanup_simulation_branch", lambda cwd: None)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr(
            "main.self_improve.run_quality_gate",
            lambda cwd: type("QualityResult", (), {"passed": True, "summary": "ok"})(),
        )
        monkeypatch.setattr(
            "main.self_improve.validate_code_structure",
            lambda cwd, **kwargs: type(
                "StructureResult",
                (),
                {"passed": True, "summary": "ok", "violations": []},
            )(),
        )
        monkeypatch.setattr("main.self_improve._metrics_stable", lambda *args, **kwargs: (True, "stable"))
        monkeypatch.setattr(
            "main.self_improve._git_commit_all",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("simulate should not commit")),
        )
        monkeypatch.setattr(
            "main.self_improve._create_pr",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("simulate should not create PRs")),
        )

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.flow_id = "flow-sim-report"
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = str(tmp_path / "runtime" / "prd.json")
        mock_flow.state.prd_path_md = str(tmp_path / "runtime" / "prd.md")

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": str(tmp_path / "runtime" / "plan.json"),
            "plan_path_md": str(tmp_path / "runtime" / "plan.md"),
        }
        mock_exec = {
            "overall_success": True,
            "story_status": "completed",
            "run_id": "sim-run-report",
            "task_flow_ids": {"T-001": "task-flow-sim-report"},
            "output_path": str(tmp_path / "runtime" / "exec"),
            "report_path": str(tmp_path / "runtime" / "exec" / "report.json"),
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        run_self_improve(simulate=True)

        out = capsys.readouterr().out

        assert "Simulation report" in out
        assert str(tmp_path / "runtime" / "prd.json") in out
        assert str(tmp_path / "runtime" / "plan.json") in out
        assert str(tmp_path / "runtime" / "exec" / "report.json") in out
        assert "completed" in out

    def test_simulate_runs_full_flow_without_persisting_branch_changes(
        self,
        tmp_path,
        monkeypatch,
        store,
        capsys,
    ):
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
        monkeypatch.setattr("main.self_improve._run_git_preflight", lambda *args, **kwargs: None)

        prepared = []
        cleaned = []
        prioritized = []

        monkeypatch.setattr(
            "main.self_improve._prepare_simulation_branch",
            lambda cwd: (prepared.append(str(cwd)) or True, SIMULATION_BRANCH_NAME),
        )
        monkeypatch.setattr(
            "main.self_improve._cleanup_simulation_branch",
            lambda cwd: cleaned.append(str(cwd)),
        )

        def fake_prioritize(opps, **kwargs):
            del kwargs
            prioritized.append(len(opps))
            return opps

        monkeypatch.setattr("main.self_improve.dialectic_prioritize", fake_prioritize)
        monkeypatch.setattr(
            "main.self_improve.run_quality_gate",
            lambda cwd: type("QualityResult", (), {"passed": True, "summary": "ok"})(),
        )
        monkeypatch.setattr(
            "main.self_improve.validate_code_structure",
            lambda cwd, **kwargs: type(
                "StructureResult",
                (),
                {"passed": True, "summary": "ok", "violations": []},
            )(),
        )
        monkeypatch.setattr("main.self_improve._metrics_stable", lambda *args, **kwargs: (True, "stable"))
        monkeypatch.setattr(
            "main.self_improve._git_commit_all",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("simulate should not commit")),
        )
        monkeypatch.setattr(
            "main.self_improve._create_pr",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("simulate should not create PRs")),
        )
        monkeypatch.setattr(
            "main.self_improve._mark_roadmap_items_completed",
            lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("simulate should not mutate roadmap")),
        )

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.flow_id = "flow-sim"
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = str(tmp_path / "runtime" / "prd.json")
        mock_flow.state.prd_path_md = str(tmp_path / "runtime" / "prd.md")

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": str(tmp_path / "runtime" / "plan.json"),
            "plan_path_md": str(tmp_path / "runtime" / "plan.md"),
        }
        mock_exec = {
            "overall_success": True,
            "story_status": "completed",
            "run_id": "sim-run",
            "task_flow_ids": {"T-001": "task-flow-sim"},
            "output_path": str(tmp_path / "runtime" / "exec"),
            "report_path": str(tmp_path / "runtime" / "exec" / "report.json"),
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(simulate=True)
        out = capsys.readouterr().out

        assert record.failure_reason == "simulated"
        assert record.prd_generated is True
        assert record.plan_generated is True
        assert record.execution_attempted is True
        assert prioritized == [record.opportunities_found]
        assert prepared == [str(tmp_path)]
        assert cleaned == [str(tmp_path)]
        assert (
            f"[3/7] Using previously prepared disposable simulation branch: "
            f"{SIMULATION_BRANCH_NAME}"
        ) in out

    def test_simulation_uses_persistent_runtime_root_for_artifacts(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Persist simulation artifacts\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr("main.self_improve._run_git_preflight", lambda *args, **kwargs: None)
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.dialectic_prioritize", lambda opps, **kw: opps)
        monkeypatch.setattr(
            "main.self_improve._prepare_simulation_branch",
            lambda cwd: (True, SIMULATION_BRANCH_NAME),
        )
        monkeypatch.setattr("main.self_improve._cleanup_simulation_branch", lambda cwd: None)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr(
            "main.self_improve.run_quality_gate",
            lambda cwd: type("QualityResult", (), {"passed": True, "summary": "ok"})(),
        )
        monkeypatch.setattr(
            "main.self_improve.validate_code_structure",
            lambda cwd, **kwargs: type(
                "StructureResult",
                (),
                {"passed": True, "summary": "ok", "violations": []},
            )(),
        )
        monkeypatch.setattr("main.self_improve._metrics_stable", lambda *args, **kwargs: (True, "stable"))

        runtime_root = tmp_path / ".dialectic" / "self_improve" / "simulations" / "cycle-persist"
        monkeypatch.setattr(
            "main.self_improve._simulation_runtime_root",
            lambda project_root, cycle_id: runtime_root,
        )

        def _write(path: Path, content: str = "{}") -> str:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return str(path)

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.flow_id = "flow-sim-persist"
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = _write(runtime_root / "prd_output" / "self" / "prd.json")
        mock_flow.state.prd_path_md = _write(runtime_root / "prd_output" / "self" / "prd.md", "# prd\n")

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": _write(runtime_root / "prd_output" / "self" / "plan.json"),
            "plan_path_md": _write(runtime_root / "prd_output" / "self" / "plan.md", "# plan\n"),
        }
        mock_exec = {
            "overall_success": True,
            "story_status": "completed",
            "run_id": "sim-run-persist",
            "task_flow_ids": {"T-001": "task-flow-sim-persist"},
            "output_path": _write(runtime_root / "exec_output" / "self" / "run-persist" / "checkpoint.json"),
            "report_path": _write(runtime_root / "exec_output" / "self" / "run-persist" / "report.json"),
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(simulate=True)

        assert record.failure_reason == "simulated"
        assert record.prd_path_json.startswith(str(tmp_path / ".dialectic" / "self_improve"))
        assert Path(record.prd_path_json).exists()
        assert Path(record.plan_path_json).exists()
        assert Path(record.execution_report_path).exists()

    def test_simulation_retries_failed_execution_once_before_success(
        self,
        tmp_path,
        monkeypatch,
        store,
        capsys,
    ):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Retry failed execution\n")

        monkeypatch.setenv("SELF_IMPROVE_EXECUTION_RETRIES", "1")
        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr("main.self_improve._run_git_preflight", lambda *args, **kwargs: None)
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.dialectic_prioritize", lambda opps, **kw: opps)
        monkeypatch.setattr(
            "main.self_improve._prepare_simulation_branch",
            lambda cwd: (True, SIMULATION_BRANCH_NAME),
        )
        monkeypatch.setattr("main.self_improve._cleanup_simulation_branch", lambda cwd: None)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr(
            "main.self_improve.run_quality_gate",
            lambda cwd: type("QualityResult", (), {"passed": True, "summary": "ok"})(),
        )
        monkeypatch.setattr(
            "main.self_improve.validate_code_structure",
            lambda cwd, **kwargs: type(
                "StructureResult",
                (),
                {"passed": True, "summary": "ok", "violations": []},
            )(),
        )
        monkeypatch.setattr("main.self_improve._metrics_stable", lambda *args, **kwargs: (True, "stable"))

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.flow_id = "flow-sim-retry"
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = str(tmp_path / "runtime" / "prd.json")
        mock_flow.state.prd_path_md = str(tmp_path / "runtime" / "prd.md")

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": str(tmp_path / "runtime" / "plan.json"),
            "plan_path_md": str(tmp_path / "runtime" / "plan.md"),
        }

        attempts = {"count": 0}

        def fake_execution(**kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                return {
                    "overall_success": False,
                    "story_status": "failed",
                    "run_id": "sim-run-retry-1",
                    "task_flow_ids": {},
                    "output_path": str(tmp_path / "runtime" / "exec-1"),
                    "report_path": str(tmp_path / "runtime" / "exec-1" / "report.json"),
                }
            return {
                "overall_success": True,
                "story_status": "completed",
                "run_id": "sim-run-retry-2",
                "task_flow_ids": {"T-001": "task-flow-sim-retry"},
                "output_path": str(tmp_path / "runtime" / "exec-2"),
                "report_path": str(tmp_path / "runtime" / "exec-2" / "report.json"),
            }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", side_effect=fake_execution):
                        record = run_self_improve(simulate=True)

        out = capsys.readouterr().out

        assert record.failure_reason == "simulated"
        assert attempts["count"] == 2
        assert record.execution_attempt_count == 2
        assert record.execution_failure_reasons == ["Execution failed: failed"]
        assert "Retrying execution from the approved plan" in out

    def test_simulation_stops_after_configured_execution_retries_exhausted(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Exhaust failed execution retries\n")

        monkeypatch.setenv("SELF_IMPROVE_EXECUTION_RETRIES", "1")
        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr("main.self_improve._run_git_preflight", lambda *args, **kwargs: None)
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.dialectic_prioritize", lambda opps, **kw: opps)
        monkeypatch.setattr(
            "main.self_improve._prepare_simulation_branch",
            lambda cwd: (True, SIMULATION_BRANCH_NAME),
        )
        monkeypatch.setattr("main.self_improve._cleanup_simulation_branch", lambda cwd: None)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.flow_id = "flow-sim-retry-fail"
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = str(tmp_path / "runtime" / "prd.json")
        mock_flow.state.prd_path_md = str(tmp_path / "runtime" / "prd.md")

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": str(tmp_path / "runtime" / "plan.json"),
            "plan_path_md": str(tmp_path / "runtime" / "plan.md"),
        }

        failed_exec = {
            "overall_success": False,
            "story_status": "failed",
            "run_id": "sim-run-retry-fail",
            "task_flow_ids": {},
            "output_path": str(tmp_path / "runtime" / "exec-fail"),
            "report_path": str(tmp_path / "runtime" / "exec-fail" / "report.json"),
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", side_effect=[failed_exec, failed_exec]):
                        record = run_self_improve(simulate=True)

        assert record.failure_reason == "Execution failed: failed"
        assert record.execution_attempt_count == 2
        assert record.execution_failure_reasons == [
            "Execution failed: failed",
            "Execution failed: failed",
        ]

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

    def test_accepts_strong_prd_at_self_improve_floor(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Accept strong PRDs at the self-improve score floor\n")

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

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.state.quality_score = 8.5
        mock_flow.state.consensus_reached = False
        mock_flow.state.prd_path_json = str(tmp_path / "prd_output" / "PRD_strong.json")
        mock_flow.state.prd_path_md = str(tmp_path / "prd_output" / "PRD_strong.md")

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": str(tmp_path / "prd_output" / "exec_strong.json"),
            "plan_path_md": str(tmp_path / "prd_output" / "exec_strong.md"),
        }
        mock_exec = {
            "overall_success": True,
            "story_status": "completed",
            "run_id": "run-strong-prd",
            "task_flow_ids": {"T-001": "task-flow-strong-prd"},
            "output_path": str(tmp_path / "exec_output" / "run-strong-prd"),
            "report_path": str(tmp_path / "exec_output" / "run-strong-prd" / "report.json"),
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan) as mock_plan_run:
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(max_improvements=1)

        mock_plan_run.assert_called_once()
        assert record.prd_generated is True
        assert record.plan_generated is True
        assert record.execution_attempted is True
        assert "PRD quality too low" not in record.failure_reason

    def test_creates_commit_before_pr(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        roadmap = tmp_path / "internal" / "ROADMAP.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("# Anti-drift only\n")
        roadmap.write_text("- [ ] Improve PR handoff\n")

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

    def test_marks_selected_roadmap_items_complete_after_success(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        roadmap = tmp_path / "internal" / "ROADMAP.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("# Anti-drift only\n")
        roadmap.write_text(
            "- [ ] Improve PR handoff\n"
            "- [ ] Keep another item pending\n",
            encoding="utf-8",
        )

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
                        run_self_improve(max_improvements=1)

        roadmap_text = roadmap.read_text(encoding="utf-8")
        assert "- [x] Improve PR handoff" in roadmap_text
        assert "- [ ] Keep another item pending" in roadmap_text

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
        from src.main.self_improve import _save_self_improve_record
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
        assert "Execution run: run-123" not in out

    def test_resume_switches_to_recorded_branch_when_current_branch_drifted(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        from src.main.self_improve import _save_self_improve_record
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
        from src.main.self_improve import _save_self_improve_record
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

    def test_resume_recreates_missing_recorded_branch_from_main_when_artifacts_exist(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        from src.main.self_improve import _save_self_improve_record
        from schemas import ImprovementOpportunity

        git_dir = tmp_path / ".git"
        git_dir.write_text("gitdir: /fake/worktree\n")

        prd_path = tmp_path / "prd_output" / "PRD_test.json"
        plan_path = tmp_path / "prd_output" / "exec_test.json"
        execution_output = tmp_path / "exec_output" / "run-456" / "checkpoint.json"
        execution_report = tmp_path / "exec_output" / "run-456" / "report.json"
        for path in (prd_path, plan_path, execution_output, execution_report):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")

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
        monkeypatch.setattr("main.self_improve._git_current_branch", lambda cwd: "main")
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
            cycle_id="cycle-main-recreate",
            timestamp="2026-03-10T00:00:00Z",
            baseline_metrics={"prd_score": {"count": 0, "mean": 0}},
            selected_opportunities=[
                ImprovementOpportunity(
                    id="opp-1",
                    category="code_health",
                    title="Recreate missing branch from main",
                    description="Resume should recover the recorded branch when reusable artifacts exist.",
                    evidence=[".dialectic/self_improve/cycle-main-recreate.json"],
                    estimated_impact="high",
                )
            ],
            opportunities_found=1,
            opportunities_attempted=1,
            prd_generated=True,
            plan_generated=True,
            execution_attempted=True,
            tests_passed=False,
            branch_name="self-improve/cycle-main-recreate",
            prd_path_json=str(prd_path),
            plan_path_json=str(plan_path),
            execution_run_id="run-456",
            execution_output_path=str(execution_output),
            execution_report_path=str(execution_report),
            failure_reason="Tests failed after execution",
        )
        _save_self_improve_record(tmp_path, record)

        resumed = run_self_improve(resume_cycle_id="cycle-main-recreate")

        assert resumed.failure_reason == ""
        assert recreated == [("self-improve/cycle-main-recreate", str(tmp_path))]

    def test_resume_reenters_execution_when_saved_execution_story_failed(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        from src.main.self_improve import _save_self_improve_record
        from schemas import ImprovementOpportunity

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr(
            "main.self_improve.run_quality_gate",
            lambda cwd: type("QualityResult", (), {"passed": True, "summary": "ok"})(),
        )
        monkeypatch.setattr(
            "main.self_improve.validate_code_structure",
            lambda cwd, **kwargs: type(
                "StructureResult",
                (),
                {"passed": True, "summary": "ok", "violations": []},
            )(),
        )
        monkeypatch.setattr("main.self_improve._metrics_stable", lambda *args, **kwargs: (True, "stable"))
        monkeypatch.setattr(
            "main.self_improve._git_commit_all",
            lambda cwd, message: (False, "nothing to commit"),
        )
        monkeypatch.setattr(
            "main.self_improve._git_has_commits_ahead",
            lambda cwd, base_branch="main": (False, f"no commits ahead of {base_branch}"),
        )
        monkeypatch.setattr("main.self_improve._create_pr", lambda *args, **kwargs: None)

        prd_path = tmp_path / "prd_output" / "PRD_test.json"
        plan_path = tmp_path / "prd_output" / "exec_test.json"
        execution_output = tmp_path / "exec_output" / "run-789" / "checkpoint.json"
        execution_report = tmp_path / "exec_output" / "run-789" / "report.json"
        for path in (prd_path, plan_path, execution_output, execution_report):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")

        record = SelfImprovementRecord(
            cycle_id="cycle-rerun-execution",
            timestamp="2026-03-10T00:00:00Z",
            baseline_metrics={"prd_score": {"count": 0, "mean": 0}},
            selected_opportunities=[
                ImprovementOpportunity(
                    id="opp-1",
                    category="code_health",
                    title="Retry failed execution",
                    description="Resume should rerun failed execution instead of reusing its artifacts.",
                    evidence=[str(execution_report)],
                    estimated_impact="high",
                )
            ],
            opportunities_found=1,
            opportunities_attempted=1,
            prd_generated=True,
            plan_generated=True,
            execution_attempted=True,
            tests_passed=True,
            metrics_stable=True,
            pr_created=True,
            prd_path_json=str(prd_path),
            plan_path_json=str(plan_path),
            execution_run_id="run-789",
            execution_story_status="failed",
            execution_output_path=str(execution_output),
            execution_report_path=str(execution_report),
            failure_reason="",
        )
        _save_self_improve_record(tmp_path, record)

        execution_calls: list[dict[str, object]] = []

        monkeypatch.setattr(
            "execution.dialectic_execution.run_dialectic_execution",
            lambda **kwargs: (
                execution_calls.append(kwargs)
                or {
                    "overall_success": True,
                    "story_status": "completed",
                    "run_id": "run-789",
                    "task_flow_ids": {"T-001": "task-flow-rerun"},
                    "output_path": str(tmp_path / "exec_output" / "run-789"),
                    "report_path": str(tmp_path / "exec_output" / "run-789" / "report.json"),
                }
            ),
        )

        resumed = run_self_improve(resume_cycle_id="cycle-rerun-execution")

        assert resumed.execution_story_status == "completed"
        assert len(execution_calls) == 1
        assert execution_calls[0]["plan_path"] == str(plan_path)
        assert execution_calls[0]["resume_run_id"] == "run-789"


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

    def test_prefers_execution_when_saved_story_status_failed_even_without_failure_reason(self):
        summary = _summarize_resume_state(
            SelfImprovementRecord(
                cycle_id="c1b",
                timestamp="2026-03-10T00:00:00Z",
                prd_generated=True,
                plan_generated=True,
                execution_attempted=True,
                tests_passed=True,
                metrics_stable=True,
                pr_created=True,
                prd_path_json="prd.json",
                plan_path_json="plan.json",
                execution_run_id="run-2",
                execution_story_status="failed",
                execution_output_path="exec-output.json",
                execution_report_path="exec-report.json",
            ),
            "",
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
        from src.main.self_improve import _save_self_improve_record

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


class TestFailureBranchPreservation:
    def test_preserves_branch_when_post_execution_tests_fail(
        self,
        tmp_path,
        monkeypatch,
        store,
    ):
        from schemas import ImprovementOpportunity, IntrospectionReport
        from unittest.mock import MagicMock, patch

        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Preserve failed cycle branches\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve._run_git_preflight", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            "main.self_improve.dialectic_prioritize",
            lambda opps, **kw: opps,
        )
        monkeypatch.setattr(
            "main.self_improve.run_introspection",
            lambda **kwargs: IntrospectionReport(
                timestamp="2026-03-10T00:00:00Z",
                opportunities=[
                    ImprovementOpportunity(
                        id="opp-1",
                        category="code_health",
                        title="Preserve failure branch",
                        description="Keep the failed self-improve branch for resume.",
                        evidence=["internal/ROADMAP.md"],
                        estimated_impact="high",
                    )
                ],
                baseline_metrics={},
            ),
        )
        monkeypatch.setattr("main.self_improve._git_branch_create", lambda b, c: True)

        discard_calls = []
        monkeypatch.setattr(
            "main.self_improve._git_discard_branch",
            lambda branch, cwd: discard_calls.append((branch, str(cwd))),
        )

        snapshot_results = iter(
            [
                {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
                {"returncode": 1, "passed": False, "stdout_tail": "1 failed\n", "stderr_tail": ""},
            ]
        )
        monkeypatch.setattr("main.self_improve._snapshot_tests", lambda p: next(snapshot_results))
        monkeypatch.setattr(
            "main.self_improve.run_quality_gate",
            lambda cwd: type("QualityResult", (), {"passed": True, "summary": "ok"})(),
        )
        monkeypatch.setattr(
            "main.self_improve.validate_code_structure",
            lambda cwd, **kwargs: type(
                "StructureResult",
                (),
                {"passed": True, "summary": "ok", "violations": []},
            )(),
        )

        mock_flow = MagicMock()
        mock_flow.flow_id = "flow-preserve"
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = str(tmp_path / "runtime" / "prd.json")
        mock_flow.state.prd_path_md = str(tmp_path / "runtime" / "prd.md")

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": str(tmp_path / "runtime" / "plan.json"),
            "plan_path_md": str(tmp_path / "runtime" / "plan.md"),
        }
        mock_exec = {
            "overall_success": True,
            "story_status": "completed",
            "run_id": "run-preserve",
            "task_flow_ids": {"T-001": "task-flow-preserve"},
            "output_path": str(tmp_path / "runtime" / "exec"),
            "report_path": str(tmp_path / "runtime" / "exec" / "report.json"),
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(max_improvements=1)

        assert record.failure_reason == "Tests failed after execution"
        assert record.branch_name.startswith("self-improve/")
        assert not discard_calls


class TestTransientLlmRetries:
    def test_detects_transient_timeout_messages(self):
        assert _is_transient_llm_error(RuntimeError("Failed to connect to OpenAI API: Request timed out."))
        assert _is_transient_llm_error(RuntimeError("Rate limit exceeded"))
        assert not _is_transient_llm_error(RuntimeError("Invalid API key"))

    def test_retries_only_transient_failures(self, monkeypatch):
        monkeypatch.setenv("SELF_IMPROVE_LLM_STAGE_RETRIES", "2")
        monkeypatch.setenv("SELF_IMPROVE_LLM_RETRY_BACKOFF_SECONDS", "0")

        attempts = {"count": 0}

        def flaky_operation():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("Failed to connect to OpenAI API: Request timed out.")
            return "ok"

        assert _run_with_transient_llm_retries("planning", flaky_operation) == "ok"
        assert attempts["count"] == 3


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
            logger=cast(
                Any,
                type("Logger", (), {"warning": lambda self, msg, *args: None})(),
            ),
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

    def test_simulate_does_not_leak_hooks_after_run(self, tmp_path, monkeypatch, store):
        from crewai.hooks import get_before_llm_call_hooks, clear_all_global_hooks
        clear_all_global_hooks()
        self._setup_introspection(tmp_path, monkeypatch, store)

        monkeypatch.setattr("main.self_improve._run_git_preflight", lambda *args, **kwargs: None)
        monkeypatch.setattr(
            "main.self_improve._prepare_simulation_branch",
            lambda cwd: (True, SIMULATION_BRANCH_NAME),
        )
        monkeypatch.setattr("main.self_improve._cleanup_simulation_branch", lambda cwd: None)
        monkeypatch.setattr("main.self_improve.dialectic_prioritize", lambda opps, **kw: opps)
        monkeypatch.setattr(
            "main.self_improve.run_quality_gate",
            lambda cwd: type("QualityResult", (), {"passed": True, "summary": "ok"})(),
        )
        monkeypatch.setattr(
            "main.self_improve.validate_code_structure",
            lambda cwd, **kwargs: type(
                "StructureResult",
                (),
                {"passed": True, "summary": "ok", "violations": []},
            )(),
        )
        monkeypatch.setattr("main.self_improve._metrics_stable", lambda *args, **kwargs: (True, "stable"))
        monkeypatch.setattr("main.self_improve._git_commit_all", lambda *args, **kwargs: (False, "nothing to commit"))

        from unittest.mock import MagicMock, patch

        mock_flow = MagicMock()
        mock_flow.flow_id = "flow-hooks"
        mock_flow.state.quality_score = 9.5
        mock_flow.state.consensus_reached = True
        mock_flow.state.prd_path_json = "fake_prd.json"
        mock_flow.state.prd_path_md = "fake_prd.md"

        mock_plan = {
            "quality_score": 9.0,
            "plan_path_json": "fake_plan.json",
            "plan_path_md": "fake_plan.md",
        }
        mock_exec = {
            "overall_success": True,
            "story_status": "completed",
            "run_id": "hook-run",
            "task_flow_ids": {"T-001": "task-flow-hook"},
            "output_path": "fake_exec",
            "report_path": "fake_exec/report.json",
        }

        with patch("dialectic.prd_flow.DialecticFlow", return_value=mock_flow):
            with patch("dialectic.prd_flow._get_persistence", return_value=MagicMock()):
                with patch("planning.flow.run_user_story_planning", return_value=mock_plan):
                    with patch("execution.dialectic_execution.run_dialectic_execution", return_value=mock_exec):
                        record = run_self_improve(simulate=True)

        assert record.failure_reason == "simulated"
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
                record = run_self_improve(simulate=False, max_improvements=1)

        assert record.opportunities_attempted >= 1
        assert record.failure_reason != ""
