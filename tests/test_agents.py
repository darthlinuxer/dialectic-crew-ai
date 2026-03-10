"""Tests for dialectic.agents helpers."""

from pathlib import Path

import dialectic.agents as agents
from dialectic.vision import VisionContext


def test_vision_knowledge_preserves_absolute_paths(monkeypatch, tmp_path):
    project_vision = tmp_path / "knowledge" / "VISION.md"
    self_vision = tmp_path / "internal" / "SELF_VISION.md"
    captured_paths: list[list[Path]] = []

    def fake_text_file_knowledge_source(*, file_paths):
        captured_paths.append(file_paths)
        return {"file_paths": file_paths}

    monkeypatch.setattr(agents, "prepare_vision_runtime", lambda context: None)
    monkeypatch.setattr(
        agents,
        "get_vision_path",
        lambda context: self_vision if context is VisionContext.SELF else project_vision,
    )
    monkeypatch.setattr(
        agents,
        "TextFileKnowledgeSource",
        fake_text_file_knowledge_source,
    )

    project_result = agents.vision_knowledge(VisionContext.PROJECT)
    self_result = agents.vision_knowledge(VisionContext.SELF)

    assert project_result["file_paths"] == [project_vision]
    assert self_result["file_paths"] == [self_vision]
    assert captured_paths == [[project_vision], [self_vision]]
    assert all(isinstance(paths[0], Path) for paths in captured_paths)
