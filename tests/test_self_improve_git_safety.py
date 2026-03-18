"""Focused tests for self-improve git safety helpers and preflight."""

# pylint: disable=missing-class-docstring,missing-function-docstring
# pylint: disable=redefined-outer-name,unused-argument,too-few-public-methods
# pylint: disable=line-too-long,too-many-arguments,too-many-positional-arguments
# pylint: disable=duplicate-code

import os
import subprocess
from pathlib import Path

import pytest

from dialectic.metrics import MetricsStore, _reset_metrics_store
from src.main.self_improve import (
    SIMULATION_BRANCH_NAME,
    _git_worktree_clean,
    _prepare_simulation_branch,
    _recover_stale_self_improve_worktree,
    run_self_improve,
)
from src.main.self_improve.git_helpers import run_cmd


@pytest.fixture(autouse=True)
def _reset_singleton():
    _reset_metrics_store()
    yield
    _reset_metrics_store()


@pytest.fixture
def store(tmp_path):
    return MetricsStore(db_path=tmp_path / "test_self_improve_git_safety.db")


class TestGitWorktreeClean:
    def test_returns_clean_when_status_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "main.self_improve._run_cmd",
            lambda cmd, cwd=None, timeout=120: subprocess.CompletedProcess(
                cmd, 0, stdout="", stderr=""
            ),
        )

        clean, reason = _git_worktree_clean(tmp_path)

        assert clean is True
        assert reason == "clean"

    def test_returns_dirty_summary_when_status_has_changes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "main.self_improve._run_cmd",
            lambda cmd, cwd=None, timeout=120: subprocess.CompletedProcess(
                cmd,
                0,
                stdout=" M metrics.db\n?? scratch.txt\n",
                stderr="",
            ),
        )

        clean, reason = _git_worktree_clean(tmp_path)

        assert clean is False
        assert "metrics.db" in reason
        assert "scratch.txt" in reason


class TestRunCmd:
    def test_clamps_timeout_to_minimum_one_second(self, monkeypatch):
        captured = {}

        def fake_subprocess_run(cmd, capture_output, text, check, timeout, cwd):
            captured["timeout"] = timeout
            captured["cwd"] = cwd
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(
            "src.main.self_improve.git_helpers.subprocess.run",
            fake_subprocess_run,
        )

        run_cmd(["git", "status"], cwd=Path("."), timeout=0)

        assert captured["timeout"] == 1
        assert captured["cwd"] == "."


class TestRecoverStaleSelfImproveWorktree:
    def test_skips_recovery_outside_self_improve_branch(self, tmp_path, monkeypatch):
        monkeypatch.setattr("main.self_improve._git_current_branch", lambda cwd: "main")

        recovered, reason = _recover_stale_self_improve_worktree(tmp_path)

        assert recovered is False
        assert reason == "not on a self-improve branch"

    def test_resets_and_cleans_self_improve_branch(self, tmp_path, monkeypatch):
        seen_cmds = []

        def fake_run(cmd, cwd=None, timeout=120):
            seen_cmds.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(
            "main.self_improve._git_current_branch",
            lambda cwd: "self-improve/20260310T000000",
        )
        monkeypatch.setattr("main.self_improve._run_cmd", fake_run)

        recovered, reason = _recover_stale_self_improve_worktree(tmp_path)

        assert recovered is True
        assert "discarded stale self-improve worktree" in reason
        assert seen_cmds == [
            ["git", "reset", "--hard", "HEAD"],
            ["git", "clean", "-fd"],
        ]


class TestPrepareSimulationBranch:
    def test_deletes_existing_simulation_branch_before_recreating(
        self, tmp_path, monkeypatch
    ):
        deleted = []
        created = []

        monkeypatch.setattr("main.self_improve._git_current_branch", lambda cwd: "main")
        monkeypatch.setattr(
            "main.self_improve._git_branch_exists",
            lambda branch, cwd: branch == SIMULATION_BRANCH_NAME,
        )
        monkeypatch.setattr(
            "main.self_improve._git_delete_branch",
            lambda branch, cwd: (
                deleted.append((branch, str(cwd))) or True,
                f"deleted {branch}",
            ),
        )
        monkeypatch.setattr(
            "main.self_improve._git_branch_create",
            lambda branch, cwd: created.append((branch, str(cwd))) or True,
        )

        prepared, branch_name = _prepare_simulation_branch(tmp_path)

        assert prepared is True
        assert branch_name == SIMULATION_BRANCH_NAME
        assert deleted == [(SIMULATION_BRANCH_NAME, str(tmp_path))]
        assert created == [(SIMULATION_BRANCH_NAME, str(tmp_path))]


class TestSelfImproveWorktreePreflight:
    def test_factory_workspace_dir_is_gitignored(self):
        gitignore_path = Path(__file__).resolve().parents[1] / ".gitignore"
        entries = {
            line.strip()
            for line in gitignore_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        assert ".factory/" in entries

    def test_aborts_when_worktree_is_dirty(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Require clean worktree\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {
                "returncode": 0,
                "passed": True,
                "stdout_tail": "",
                "stderr_tail": "",
            },
        )
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr(
            "dialectic.introspect.resolve_project_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            "main.self_improve.dialectic_prioritize", lambda opps, **kw: opps
        )
        monkeypatch.setattr(
            "main.self_improve.shutil.which",
            lambda name: "/usr/bin/git" if name == "git" else "/usr/bin/uv",
        )
        monkeypatch.setattr(
            "main.self_improve._git_worktree_clean",
            lambda cwd: (False, "Worktree has uncommitted changes: M metrics.db"),
        )

        record = run_self_improve(max_improvements=1)

        assert "Worktree has uncommitted changes" in record.failure_reason
        assert "Commit the changes" in record.failure_reason
        assert "--stash-dirty" in record.failure_reason

    def test_stashes_dirty_non_self_improve_branch_when_requested(
        self, tmp_path, monkeypatch, store, capsys
    ):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Allow stash-dirty preflight\n")

        states = iter(
            [
                (False, "Worktree has uncommitted changes: M metrics.db"),
                (True, "clean"),
            ]
        )
        stash_messages = []

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {
                "returncode": 0,
                "passed": True,
                "stdout_tail": "",
                "stderr_tail": "",
            },
        )
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr(
            "dialectic.introspect.resolve_project_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            "main.self_improve.dialectic_prioritize", lambda opps, **kw: opps
        )
        monkeypatch.setattr(
            "main.self_improve.shutil.which",
            lambda name: "/usr/bin/git" if name == "git" else "/usr/bin/uv",
        )
        monkeypatch.setattr("main.self_improve._git_current_branch", lambda cwd: "main")
        monkeypatch.setattr(
            "main.self_improve._git_worktree_clean", lambda cwd: next(states)
        )
        monkeypatch.setattr(
            "main.self_improve._recover_stale_self_improve_worktree",
            lambda cwd: (False, "not on a self-improve branch"),
        )

        def fake_stash(cwd, message):
            stash_messages.append(message)
            return True, "Saved working directory and index state"

        monkeypatch.setattr("main.self_improve._git_stash_worktree", fake_stash)
        monkeypatch.setattr("main.self_improve._git_branch_create", lambda b, c: False)

        record = run_self_improve(max_improvements=1, stash_dirty=True)
        out = capsys.readouterr().out

        assert stash_messages == [f"self-improve-preflight/{record.cycle_id}"]
        assert "Stashed current branch changes" in out
        assert record.failure_reason == "Failed to create git branch"

    def test_reports_stash_failure_with_guidance(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Show stash failure guidance\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {
                "returncode": 0,
                "passed": True,
                "stdout_tail": "",
                "stderr_tail": "",
            },
        )
        monkeypatch.setattr(
            "main.self_improve.shutil.which",
            lambda name: "/usr/bin/git" if name == "git" else "/usr/bin/uv",
        )
        monkeypatch.setattr("main.self_improve._git_current_branch", lambda cwd: "main")
        monkeypatch.setattr(
            "main.self_improve._git_worktree_clean",
            lambda cwd: (False, "Worktree has uncommitted changes: M metrics.db"),
        )
        monkeypatch.setattr(
            "main.self_improve._recover_stale_self_improve_worktree",
            lambda cwd: (False, "not on a self-improve branch"),
        )
        monkeypatch.setattr(
            "main.self_improve._git_stash_worktree",
            lambda cwd, message: (False, "failed to stash current branch changes"),
        )

        record = run_self_improve(max_improvements=1, stash_dirty=True)

        assert "failed to stash current branch changes" in record.failure_reason
        assert "--stash-dirty" in record.failure_reason

    def test_recovers_stale_self_improve_branch_before_aborting(
        self, tmp_path, monkeypatch, store, capsys
    ):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Recover stale branch\n")

        states = iter(
            [
                (False, "Worktree has uncommitted changes: M scratch.txt"),
                (True, "clean"),
            ]
        )
        recovered = []

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {
                "returncode": 0,
                "passed": True,
                "stdout_tail": "",
                "stderr_tail": "",
            },
        )
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr(
            "dialectic.introspect.resolve_project_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            "main.self_improve.dialectic_prioritize", lambda opps, **kw: opps
        )
        monkeypatch.setattr(
            "main.self_improve.shutil.which",
            lambda name: "/usr/bin/git" if name == "git" else "/usr/bin/uv",
        )
        monkeypatch.setattr(
            "main.self_improve._git_worktree_clean", lambda cwd: next(states)
        )

        def fake_recover(cwd):
            recovered.append(cwd)
            return (
                True,
                "discarded stale self-improve worktree on self-improve/20260310T000000",
            )

        monkeypatch.setattr(
            "main.self_improve._recover_stale_self_improve_worktree", fake_recover
        )
        monkeypatch.setattr("main.self_improve._git_branch_create", lambda b, c: False)

        record = run_self_improve(max_improvements=1)
        out = capsys.readouterr().out

        assert recovered == [tmp_path]
        assert "Recovered stale run" in out
        assert record.failure_reason == "Failed to create git branch"

    def test_checks_git_before_introspection(self, tmp_path, monkeypatch, store):
        introspection_called = False

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {
                "returncode": 0,
                "passed": True,
                "stdout_tail": "",
                "stderr_tail": "",
            },
        )
        monkeypatch.setattr(
            "main.self_improve.shutil.which",
            lambda name: None if name == "git" else "/usr/bin/uv",
        )

        def fail_if_called(*args, **kwargs):
            del args, kwargs
            nonlocal introspection_called
            introspection_called = True
            raise AssertionError(
                "introspection should not run when git preflight fails"
            )

        monkeypatch.setattr("main.self_improve.run_introspection", fail_if_called)

        record = run_self_improve(max_improvements=1)

        assert introspection_called is False
        assert "Git is required" in record.failure_reason

    def test_simulate_checks_git_preflight_before_baseline_tests(
        self, tmp_path, monkeypatch, store
    ):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text(
            "- [ ] Simulation should fail before baseline when git is missing\n"
        )

        baseline_called = False

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)

        def fake_snapshot_tests(project_root):
            del project_root
            nonlocal baseline_called
            baseline_called = True
            return {
                "returncode": 0,
                "passed": True,
                "stdout_tail": "",
                "stderr_tail": "",
            }

        monkeypatch.setattr("main.self_improve._snapshot_tests", fake_snapshot_tests)
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr(
            "dialectic.introspect.resolve_project_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            "main.self_improve.shutil.which",
            lambda name: None if name == "git" else "/usr/bin/uv",
        )

        record = run_self_improve(simulate=True)

        assert baseline_called is False
        assert "Git is required" in record.failure_reason

    def test_self_improve_disables_crewai_telemetry_by_default(
        self, tmp_path, monkeypatch, store
    ):
        monkeypatch.delenv("CREWAI_DISABLE_TELEMETRY", raising=False)
        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {
                "returncode": 1,
                "passed": False,
                "stdout_tail": "",
                "stderr_tail": "",
            },
        )

        run_self_improve(max_improvements=1)

        assert os.environ["CREWAI_DISABLE_TELEMETRY"] == "true"

    def test_respects_existing_telemetry_override(self, tmp_path, monkeypatch, store):
        monkeypatch.setenv("CREWAI_DISABLE_TELEMETRY", "false")
        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {
                "returncode": 1,
                "passed": False,
                "stdout_tail": "",
                "stderr_tail": "",
            },
        )

        run_self_improve(max_improvements=1)

        assert os.environ["CREWAI_DISABLE_TELEMETRY"] == "false"
