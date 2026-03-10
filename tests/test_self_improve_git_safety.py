"""Focused tests for self-improve git safety helpers and preflight."""

import os
import subprocess

import pytest

from dialectic.metrics import MetricsStore, _reset_metrics_store
from main.self_improve import _git_worktree_clean, run_self_improve


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
            lambda cmd, cwd=None, timeout=120: subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),
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


class TestSelfImproveWorktreePreflight:
    def test_aborts_when_worktree_is_dirty(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Require clean worktree\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.dialectic_prioritize", lambda opps, **kw: opps)
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

    def test_checks_git_before_introspection(self, tmp_path, monkeypatch, store):
        introspection_called = False

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr(
            "main.self_improve.shutil.which",
            lambda name: None if name == "git" else "/usr/bin/uv",
        )

        def fail_if_called(*args, **kwargs):
            nonlocal introspection_called
            introspection_called = True
            raise AssertionError("introspection should not run when git preflight fails")

        monkeypatch.setattr("main.self_improve.run_introspection", fail_if_called)

        record = run_self_improve(max_improvements=1)

        assert introspection_called is False
        assert "Git is required" in record.failure_reason

    def test_dry_run_skips_git_preflight(self, tmp_path, monkeypatch, store):
        vision = tmp_path / "internal" / "SELF_VISION.md"
        vision.parent.mkdir(parents=True, exist_ok=True)
        vision.write_text("- [ ] Dry run should skip git preflight\n")

        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 0, "passed": True, "stdout_tail": "", "stderr_tail": ""},
        )
        monkeypatch.setattr("dialectic.introspect.get_vision_path", lambda ctx: vision)
        monkeypatch.setattr("dialectic.introspect.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr(
            "main.self_improve.shutil.which",
            lambda name: None if name == "git" else "/usr/bin/uv",
        )
        monkeypatch.setattr(
            "main.self_improve._git_worktree_clean",
            lambda cwd: (_ for _ in ()).throw(AssertionError("git worktree check should not run in dry-run")),
        )

        record = run_self_improve(dry_run=True)

        assert record.failure_reason == "dry_run"

    def test_self_improve_disables_crewai_telemetry_by_default(self, tmp_path, monkeypatch, store):
        monkeypatch.delenv("CREWAI_DISABLE_TELEMETRY", raising=False)
        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 1, "passed": False, "stdout_tail": "", "stderr_tail": ""},
        )

        run_self_improve(max_improvements=1)

        assert os.environ["CREWAI_DISABLE_TELEMETRY"] == "true"

    def test_respects_existing_telemetry_override(self, tmp_path, monkeypatch, store):
        monkeypatch.setenv("CREWAI_DISABLE_TELEMETRY", "false")
        monkeypatch.setattr("main.self_improve.resolve_project_root", lambda: tmp_path)
        monkeypatch.setattr("main.self_improve.get_metrics_store", lambda: store)
        monkeypatch.setattr(
            "main.self_improve._snapshot_tests",
            lambda p: {"returncode": 1, "passed": False, "stdout_tail": "", "stderr_tail": ""},
        )

        run_self_improve(max_improvements=1)

        assert os.environ["CREWAI_DISABLE_TELEMETRY"] == "false"