"""Focused tests for self-improve git safety helpers and preflight."""

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