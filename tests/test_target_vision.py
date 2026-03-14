"""Tests for target-aware vision and knowledge resolution."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import dialectic.knowledge as knowledge
import dialectic.target as target
import dialectic.vision as vision
from dialectic.target import TargetConfig
from dialectic.vision import VisionContext


vision_path_helper = cast(Any, knowledge.__dict__["_vision_path"])


def _app_root(tmp_path: Path) -> Path:
    app_root = tmp_path / "app"
    (app_root / "knowledge").mkdir(parents=True)
    (app_root / "knowledge" / "VISION.md").write_text("Default vision", encoding="utf-8")
    (app_root / "internal").mkdir(parents=True)
    (app_root / "internal" / "SELF_VISION.md").write_text("Self vision", encoding="utf-8")
    return app_root


def _target_config(app_root: Path) -> TargetConfig:
    return TargetConfig(
        target_path=app_root / ".." / "target-repo",
        set_at=datetime(2026, 3, 14, 11, 0, tzinfo=timezone.utc),
        repo_name="demo",
        repo_remote="git@github.com:octo/demo.git",
        vision_path=app_root / "knowledge" / "target" / "github-com-octo-demo--abc12345" / "VISION.md",
        target_slug="github-com-octo-demo--abc12345",
    )


def test_get_vision_path_project_uses_active_target_vision(tmp_path, monkeypatch):
    app_root = _app_root(tmp_path)
    target_config = _target_config(app_root)
    assert target_config.vision_path is not None
    target_config.vision_path.parent.mkdir(parents=True, exist_ok=True)
    target_config.vision_path.write_text("Target vision", encoding="utf-8")

    monkeypatch.setattr(vision, "resolve_app_root", lambda: app_root)
    monkeypatch.setattr(target, "_resolve_app_root", lambda: app_root)
    monkeypatch.setattr(target, "get_active_target", lambda: target_config)

    assert vision.get_vision_path(VisionContext.PROJECT) == target_config.vision_path
    assert vision.get_vision_path(VisionContext.SELF) == app_root / "internal" / "SELF_VISION.md"


def test_prepare_vision_runtime_preserves_working_directory(tmp_path, monkeypatch):
    app_root = _app_root(tmp_path)
    nested = tmp_path / "workspace" / "nested"
    nested.mkdir(parents=True)

    monkeypatch.setattr(vision, "resolve_app_root", lambda: app_root)
    monkeypatch.chdir(nested)

    resolved = vision.prepare_vision_runtime(VisionContext.SELF)

    assert resolved == app_root / "internal" / "SELF_VISION.md"
    assert Path.cwd() == nested


def test_project_prompt_path_uses_target_scoped_vision_path(tmp_path, monkeypatch):
    app_root = _app_root(tmp_path)
    target_config = _target_config(app_root)

    monkeypatch.setattr(knowledge, "resolve_project_root", lambda: app_root)
    monkeypatch.setattr(
        knowledge,
        "get_vision_path",
        lambda context: target_config.vision_path if context is VisionContext.PROJECT else app_root / "internal" / "SELF_VISION.md",
    )

    assert (
        vision_path_helper(VisionContext.PROJECT)
        == Path("knowledge/target/github-com-octo-demo--abc12345/VISION.md").as_posix()
    )
    assert vision_path_helper(VisionContext.SELF) == Path("internal/SELF_VISION.md").as_posix()


def test_crew_memory_project_uses_target_slug_namespace(tmp_path, monkeypatch):
    app_root = _app_root(tmp_path)
    captured: list[dict[str, str]] = []

    class FakeMemory:
        def __init__(self, **kwargs):
            captured.append(kwargs)

    monkeypatch.setattr(knowledge, "resolve_project_root", lambda: app_root)
    monkeypatch.setattr(
        knowledge,
        "target_memory_namespace",
        lambda namespace: f"github-com-octo-demo--abc12345/{namespace}",
    )
    monkeypatch.setattr(knowledge, "Memory", FakeMemory)

    knowledge.crew_memory(VisionContext.PROJECT, "prd")
    knowledge.crew_memory(VisionContext.SELF, "prd")

    assert captured[0]["storage"].endswith(
        "/.crewai/memory/project/github-com-octo-demo--abc12345/prd"
    )
    assert captured[1]["storage"].endswith("/.crewai/memory/self/prd")


def test_crew_memory_project_defaults_to_default_namespace(tmp_path, monkeypatch):
    app_root = _app_root(tmp_path)
    captured: list[dict[str, str]] = []

    class FakeMemory:
        def __init__(self, **kwargs):
            captured.append(kwargs)

    monkeypatch.setattr(knowledge, "resolve_project_root", lambda: app_root)
    monkeypatch.setattr(knowledge, "target_memory_namespace", lambda namespace: f"default/{namespace}")
    monkeypatch.setattr(knowledge, "Memory", FakeMemory)

    knowledge.crew_memory(VisionContext.PROJECT, "prd")

    assert captured[0]["storage"].endswith("/.crewai/memory/project/default/prd")


def test_ensure_vision_path_for_missing_target_mentions_make_vision(tmp_path, monkeypatch):
    app_root = _app_root(tmp_path)
    target_config = _target_config(app_root)

    monkeypatch.setattr(vision, "resolve_app_root", lambda: app_root)
    monkeypatch.setattr(target, "_resolve_app_root", lambda: app_root)
    monkeypatch.setattr(target, "get_active_target", lambda: target_config)

    message = ""
    try:
        vision.ensure_vision_path(VisionContext.PROJECT)
    except FileNotFoundError as exc:
        message = str(exc)

    assert "dialectic-crew make-vision" in message
    assert target_config.target_slug in message
