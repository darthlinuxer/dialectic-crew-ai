# pyright: reportPrivateUsage=none
from pathlib import Path
from typing import Any, cast

import dialectic.agents as agents
import dialectic.knowledge as knowledge
import dialectic.mcp_config as mcp_config
from dialectic.vision import VisionContext


def _lookup_private(module_dict: dict[str, object], suffix: str) -> Any:
    return module_dict[f"_{suffix}"]


vision_label = cast(Any, _lookup_private(knowledge.__dict__, "vision_label"))
python_command = cast(Any, _lookup_private(mcp_config.__dict__, "python_command"))


def test_vision_knowledge_preserves_absolute_paths(monkeypatch, tmp_path):
    project_vision = tmp_path / "knowledge" / "VISION.md"
    self_vision = tmp_path / "internal" / "SELF_VISION.md"
    captured_paths: list[list[Path]] = []

    def fake_text_file_knowledge_source(*, file_paths):
        captured_paths.append(file_paths)
        return {"file_paths": file_paths}

    monkeypatch.setattr(knowledge, "prepare_vision_runtime", lambda context: None)
    monkeypatch.setattr(
        knowledge,
        "get_vision_path",
        lambda context: self_vision if context is VisionContext.SELF else project_vision,
    )
    monkeypatch.setattr(
        knowledge,
        "TextFileKnowledgeSource",
        fake_text_file_knowledge_source,
    )

    project_result = cast(Any, knowledge.vision_knowledge(VisionContext.PROJECT))
    self_result = cast(Any, knowledge.vision_knowledge(VisionContext.SELF))

    assert project_result["file_paths"] == [project_vision]
    assert self_result["file_paths"] == [self_vision]
    assert captured_paths == [[project_vision], [self_vision]]
    assert all(isinstance(paths[0], Path) for paths in captured_paths)


def test_vision_label_matches_context():
    assert vision_label(VisionContext.PROJECT) == "VISION.md"
    assert vision_label(VisionContext.SELF) == "SELF_VISION.md"


def test_agent_factories_reference_self_vision_label():
    visionario = agents.create_visionario(VisionContext.SELF)
    critico = agents.create_critico_socratico(VisionContext.SELF)
    sintetizador = agents.create_sintetizador(VisionContext.SELF)
    validador = agents.create_validador_macro(VisionContext.SELF)
    implementer = agents.create_implementer(VisionContext.SELF)

    assert "SELF_VISION.md" in visionario.backstory
    assert "SELF_VISION.md" in critico.backstory
    assert sintetizador.role == "Dialectic Synthesizer"
    assert "SELF_VISION.md" in sintetizador.backstory
    assert "SELF_VISION.md" in validador.backstory
    assert "SELF_VISION.md" in implementer.backstory
    assert "SELF_VISION.md" in implementer.goal


def test_visionario_does_not_expose_directory_listing_tool():
    visionario = agents.create_visionario(VisionContext.SELF)

    tool_names = {getattr(tool, "name", "") for tool in (visionario.tools or [])}

    assert "list_directory" not in tool_names


def test_implementer_exposes_stack_validation_tool():
    implementer = agents.create_implementer(VisionContext.SELF)

    tool_names = {getattr(tool, "name", "") for tool in (implementer.tools or [])}

    assert "stack_aware_validation" in tool_names


def test_validador_macro_does_not_expose_file_tools():
    """Keep structured-output validation agents away from file tools."""

    validador = agents.create_validador_macro(VisionContext.SELF)

    tool_names = {getattr(tool, "name", "") for tool in (validador.tools or [])}

    assert "search_a_files_content" not in tool_names
    assert "list_directory" not in tool_names
    assert "search_a_json_content" not in tool_names


def test_crew_memory_uses_context_isolated_storage(monkeypatch, tmp_path):
    captured: list[dict] = []

    class FakeMemory:
        def __init__(self, **kwargs):
            captured.append(kwargs)

    monkeypatch.setattr(knowledge, "resolve_project_root", lambda: tmp_path)
    monkeypatch.setattr(knowledge, "Memory", FakeMemory)

    knowledge.crew_memory(VisionContext.PROJECT, "prd")
    knowledge.crew_memory(VisionContext.SELF, "prd")

    assert captured[0]["storage"].endswith("/.crewai/memory/project/default/prd")
    assert captured[1]["storage"].endswith("/.crewai/memory/self/prd")


def test_python_command_prefers_active_interpreter(monkeypatch):
    monkeypatch.setattr(mcp_config.sys, "executable", "/tmp/venv/bin/python")
    monkeypatch.setattr(mcp_config.shutil, "which", lambda name: "/usr/bin/python3")

    assert python_command() == "/tmp/venv/bin/python"


def test_python_command_falls_back_to_python3(monkeypatch):
    monkeypatch.setattr(mcp_config.sys, "executable", "")
    monkeypatch.setattr(mcp_config.shutil, "which", lambda name: "/usr/bin/python3")

    assert python_command() == "/usr/bin/python3"


def test_create_visionario_uses_yaml_config(monkeypatch):
    def fake_get_agent_config(_name):
        return {
            "role": "Custom Visionary",
            "goal": "Guard {vision_label}",
            "backstory": "Inspect {vision_label} first",
            "verbose": False,
            "allow_delegation": True,
            "reasoning": False,
            "max_reasoning_attempts": 1,
            "tool_bundle": "read_only",
            "mcp_bundle": "knowledge",
            "llm_tier": "reasoning",
        }

    monkeypatch.setattr(
        agents,
        "_get_agent_config",
        fake_get_agent_config,
    )

    agent = agents.create_visionario(VisionContext.SELF)

    assert agent.role == "Custom Visionary"
    assert agent.goal == "Guard SELF_VISION.md"
    assert agent.backstory == "Inspect SELF_VISION.md first"


def test_agent_factories_return_fresh_instances():
    first = agents.create_sintetizador(VisionContext.PROJECT)
    second = agents.create_sintetizador(VisionContext.PROJECT)

    assert first is not second
