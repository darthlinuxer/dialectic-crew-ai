import logging
import shutil
import sys
from pathlib import Path
from typing import Any

from crewai import Agent, Memory
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource

from dialectic.llm import (
    LLM_BY_TIER,
    llm_complex,
    llm_planning,
    llm_reasoning,
    llm_simple,
)
from dialectic.knowledge import crew_memory_store, vision_knowledge_source, vision_label
from dialectic.mcp_config import MCP_BUNDLES, mcp_brave_search, mcp_context7, mcp_sequential_thinking, mcp_skills
from dialectic.tool_bundles import TOOL_BUNDLES
from dialectic.vision import (
    VisionContext,
    _VISION_PATHS,
    prepare_vision_runtime,
    get_vision_path,
    resolve_project_root,
)
from dialectic.yaml_config import load_yaml_config, render_yaml_config

logger = logging.getLogger(__name__)

_AGENTS_CONFIG_PATH = Path(__file__).with_name("config") / "agents.yaml"


def _python_command() -> str:
    """Return a reliable Python executable for local stdio MCP servers."""
    return sys.executable or shutil.which("python3") or "python3"

_TOOL_BUNDLES = TOOL_BUNDLES

_MCP_BUNDLES = MCP_BUNDLES


# ---------------------------------------------------------------------------
# Knowledge source: vision document loaded via semantic chunking + vector
# retrieval.  Attach to Crew(..., knowledge_sources=[vision_knowledge(ctx)])
# so agents get relevant sections automatically.
# ---------------------------------------------------------------------------

def vision_knowledge(
    context: VisionContext = VisionContext.PROJECT,
) -> TextFileKnowledgeSource:
    """Create a TextFileKnowledgeSource for the active vision document.

    *context* selects which vision to load:
      - PROJECT (default): ``knowledge/VISION.md`` (user's project)
      - SELF: ``internal/SELF_VISION.md`` (app's own evolution)
    """
    return vision_knowledge_source(
        context,
        prepare_vision_runtime_fn=prepare_vision_runtime,
        get_vision_path_fn=get_vision_path,
        knowledge_source_cls=TextFileKnowledgeSource,
    )


def _vision_label(context: VisionContext = VisionContext.PROJECT) -> str:
    """Return the human-readable vision document name for prompts."""
    return vision_label(_VISION_PATHS, context)


def crew_memory(
    context: VisionContext = VisionContext.PROJECT,
    namespace: str = "shared",
) -> Memory:
    """Return a Memory instance isolated by vision context and crew namespace.

    Self-improve runs must not recall stale project-VISION memories, and project
    runs must not inherit self-evolution memories. Using distinct storage roots
    keeps CrewAI's persistent memory isolated while preserving memory benefits
    within each context.
    """
    return crew_memory_store(
        context,
        namespace,
        resolve_project_root_fn=resolve_project_root,
        memory_cls=Memory,
    )


def _get_agent_config(
    name: str,
    vision_context: VisionContext = VisionContext.PROJECT,
) -> dict[str, Any]:
    config = load_yaml_config(_AGENTS_CONFIG_PATH)
    try:
        return config[name]
    except KeyError as exc:
        raise KeyError(f"Unknown agent config: {name}") from exc


def _resolve_bundle(name: str, registry: dict[str, list[Any]], kind: str) -> list[Any]:
    try:
        bundle = registry[name]
    except KeyError as exc:
        raise KeyError(f"Unknown {kind} bundle: {name}") from exc
    return [item for item in bundle if item]


def build_agent_from_config(config: dict[str, Any]) -> Agent:
    """Instantiate an Agent from rendered YAML-backed config."""
    config = dict(config)

    llm_tier = config.pop("llm_tier")
    tool_bundle = config.pop("tool_bundle", "none")
    mcp_bundle = config.pop("mcp_bundle", "none")

    try:
        llm = LLM_BY_TIER[llm_tier]
    except KeyError as exc:
        raise KeyError(f"Unknown llm tier: {llm_tier}") from exc

    kwargs = {
        **config,
        "llm": llm,
        "tools": _resolve_bundle(tool_bundle, _TOOL_BUNDLES, "tool"),
    }
    mcps = _resolve_bundle(mcp_bundle, _MCP_BUNDLES, "MCP")
    if mcps:
        kwargs["mcps"] = mcps
    return Agent(**kwargs)


def _build_agent(
    name: str,
    vision_context: VisionContext = VisionContext.PROJECT,
) -> Agent:
    config = render_yaml_config(
        _get_agent_config(name, vision_context),
        {"vision_label": _vision_label(vision_context)},
    )
    return build_agent_from_config(config)


# ---------------------------------------------------------------------------
# Agent factory functions — each call returns a fresh Agent instance
# to avoid cross-flow contamination when memory=True.
# ---------------------------------------------------------------------------

def create_visionario(
    vision_context: VisionContext = VisionContext.PROJECT,
) -> Agent:
    return _build_agent("visionario", vision_context)


def create_critico_socratico(
    vision_context: VisionContext = VisionContext.PROJECT,
) -> Agent:
    return _build_agent("critico_socratico", vision_context)


def create_sintetizador(
    vision_context: VisionContext = VisionContext.PROJECT,
) -> Agent:
    return _build_agent("sintetizador", vision_context)


def create_validador_macro(
    vision_context: VisionContext = VisionContext.PROJECT,
) -> Agent:
    return _build_agent("validador_macro", vision_context)


def create_implementer(
    vision_context: VisionContext = VisionContext.PROJECT,
) -> Agent:
    return _build_agent("implementer", vision_context)
