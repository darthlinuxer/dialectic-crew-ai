"""Tests for target repository persistence and resolution helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

import dialectic.target as target


class TestTargetPersistence:
    @staticmethod
    def _app_root(tmp_path: Path) -> Path:
        app_root = tmp_path / "app"
        (app_root / ".dialectic").mkdir(parents=True)
        (app_root / "knowledge").mkdir(parents=True)
        (app_root / "knowledge" / "VISION.md").write_text("Default vision", encoding="utf-8")
        return app_root

    def test_get_active_target_returns_none_when_unset(self, tmp_path, monkeypatch):
        app_root = self._app_root(tmp_path)
        monkeypatch.setattr(target, "_resolve_app_root", lambda: app_root)

        assert target.get_active_target() is None

    def test_set_target_persists_active_target_and_registry(self, tmp_path, monkeypatch):
        app_root = self._app_root(tmp_path)
        repo_root = tmp_path / "repos" / "demo"
        repo_root.mkdir(parents=True)
        stamp = datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc)

        monkeypatch.setattr(target, "_resolve_app_root", lambda: app_root)
        monkeypatch.setattr(target, "_utcnow", lambda: stamp)
        monkeypatch.setattr(
            target,
            "_probe_git_repository",
            lambda candidate: target.GitTargetInfo(
                repo_root=repo_root,
                remote_url="git@github.com:octo/demo.git",
            ),
        )

        config = target.set_target(repo_root)
        active = target.get_active_target()
        known = target.list_known_targets()

        assert active == config
        assert config.target_path == repo_root
        assert config.repo_name == "demo"
        assert config.repo_remote == "git@github.com:octo/demo.git"
        assert config.target_slug
        assert "/" not in config.target_slug
        assert known == [config]

    def test_clear_target_keeps_known_targets_registry(self, tmp_path, monkeypatch):
        app_root = self._app_root(tmp_path)
        repo_root = tmp_path / "repos" / "demo"
        repo_root.mkdir(parents=True)

        monkeypatch.setattr(target, "_resolve_app_root", lambda: app_root)
        monkeypatch.setattr(target, "_utcnow", lambda: datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc))
        monkeypatch.setattr(
            target,
            "_probe_git_repository",
            lambda candidate: target.GitTargetInfo(repo_root=repo_root, remote_url=None),
        )

        target.set_target(repo_root)
        target.clear_target()

        assert target.get_active_target() is None
        known = target.list_known_targets()
        assert len(known) == 1
        assert known[0].target_path == repo_root

    def test_resolve_project_vision_path_prefers_active_target_vision(self, tmp_path, monkeypatch):
        app_root = self._app_root(tmp_path)
        repo_root = tmp_path / "repos" / "demo"
        repo_root.mkdir(parents=True)

        monkeypatch.setattr(target, "_resolve_app_root", lambda: app_root)
        monkeypatch.setattr(target, "_utcnow", lambda: datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc))
        monkeypatch.setattr(
            target,
            "_probe_git_repository",
            lambda candidate: target.GitTargetInfo(repo_root=repo_root, remote_url=None),
        )

        config = target.set_target(repo_root)
        vision_path = target.get_target_vision_path(config)
        vision_path.parent.mkdir(parents=True, exist_ok=True)
        vision_path.write_text("Target vision", encoding="utf-8")

        assert target.resolve_project_vision_path() == vision_path

        target.clear_target()

        assert target.resolve_project_vision_path() == app_root / "knowledge" / "VISION.md"

    def test_resolve_execution_root_uses_target_path_when_active(self, tmp_path, monkeypatch):
        app_root = self._app_root(tmp_path)
        repo_root = tmp_path / "repos" / "demo"
        repo_root.mkdir(parents=True)

        monkeypatch.setattr(target, "_resolve_app_root", lambda: app_root)
        monkeypatch.setattr(target, "_utcnow", lambda: datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc))
        monkeypatch.setattr(
            target,
            "_probe_git_repository",
            lambda candidate: target.GitTargetInfo(repo_root=repo_root, remote_url=None),
        )

        target.set_target(repo_root)
        assert target.resolve_execution_root() == repo_root

        target.clear_target()
        assert target.resolve_execution_root() == app_root

    def test_set_target_raises_for_invalid_repository(self, tmp_path, monkeypatch):
        app_root = self._app_root(tmp_path)
        candidate = tmp_path / "not-a-repo"
        candidate.mkdir()

        monkeypatch.setattr(target, "_resolve_app_root", lambda: app_root)
        monkeypatch.setattr(
            target,
            "_probe_git_repository",
            lambda candidate_path: (_ for _ in ()).throw(ValueError(f"Not a git repository: {candidate_path}")),
        )

        with pytest.raises(ValueError, match="Not a git repository"):
            target.set_target(candidate)
