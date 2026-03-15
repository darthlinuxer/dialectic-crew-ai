"""Tests for scoped artifact path resolution."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dialectic.output_paths import resolve_exec_output_dir, resolve_prd_output_dir
from dialectic.target import TargetConfig
from dialectic.vision import VisionContext
import dialectic.output_paths as output_paths


def _target_config(app_root: Path) -> TargetConfig:
    return TargetConfig(
        target_path=app_root / ".." / "target-repo",
        set_at=datetime(2026, 3, 14, 14, 0, tzinfo=timezone.utc),
        repo_name="target-repo",
        repo_remote="git@github.com:octo/target-repo.git",
        vision_path=app_root / "knowledge" / "target" / "github-com-octo-target-repo--abc12345" / "VISION.md",
        target_slug="github-com-octo-target-repo--abc12345",
    )


def test_prd_output_dir_defaults_to_default_scope(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    app_root.mkdir()
    monkeypatch.delenv(output_paths.RUNTIME_ROOT_ENV_VAR, raising=False)
    monkeypatch.setattr(output_paths, "resolve_app_root", lambda: app_root)
    monkeypatch.setattr(output_paths, "get_active_target", lambda: None)

    assert resolve_prd_output_dir(VisionContext.PROJECT) == app_root / "prd_output" / "default"
    assert resolve_prd_output_dir(VisionContext.SELF) == app_root / "prd_output" / "self"


def test_output_dirs_use_target_scope_when_active(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    app_root.mkdir()
    target_config = _target_config(app_root)
    monkeypatch.delenv(output_paths.RUNTIME_ROOT_ENV_VAR, raising=False)
    monkeypatch.setattr(output_paths, "resolve_app_root", lambda: app_root)
    monkeypatch.setattr(output_paths, "get_active_target", lambda: target_config)

    assert resolve_prd_output_dir(VisionContext.PROJECT) == (
        app_root / "prd_output" / "targets" / target_config.target_slug
    )
    assert resolve_exec_output_dir(VisionContext.PROJECT) == (
        app_root / "exec_output" / "targets" / target_config.target_slug
    )


def test_output_dirs_use_runtime_root_override(tmp_path, monkeypatch):
    app_root = tmp_path / "app"
    runtime_root = tmp_path / "runtime"
    app_root.mkdir()
    monkeypatch.setattr(output_paths, "resolve_app_root", lambda: app_root)
    monkeypatch.setattr(output_paths, "get_active_target", lambda: None)
    monkeypatch.setenv(output_paths.RUNTIME_ROOT_ENV_VAR, str(runtime_root))

    assert resolve_prd_output_dir(VisionContext.SELF) == runtime_root / "prd_output" / "self"
    assert resolve_exec_output_dir(VisionContext.PROJECT) == runtime_root / "exec_output" / "default"
