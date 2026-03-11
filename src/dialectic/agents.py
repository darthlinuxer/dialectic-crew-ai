import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from crewai import Agent, Memory
from crewai.mcp import MCPServerStdio, MCPServerHTTP
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource

from dialectic.llm import (
    LLM_BY_TIER,
    llm_complex,
    llm_planning,
    llm_reasoning,
    llm_simple,
)
from dialectic.tools import (
    file_read_tool,
    file_write_tool,
    json_search_tool,
    directory_read_tool,
    code_docs_tool,
)
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


def _make_mcp(constructor, *, required_env: str | None = None,
              required_cmd: str | None = None, **kwargs):
    """Instantiate an MCP server only when its configuration is valid.

    Returns None (with a log warning) if a required env var is unset
    or a required command is not found on PATH.
    """
    if required_env and not os.getenv(required_env):
        logger.warning("MCP server skipped: env var %s not set", required_env)
        return None
    if required_cmd and not shutil.which(required_cmd):
        logger.warning("MCP server skipped: command %r not found", required_cmd)
        return None
    try:
        return constructor(**kwargs)
    except Exception as exc:
        logger.warning("MCP server failed to initialize: %s", exc)
        return None


# ---------------------------------------------------------------------------
# MCP server configurations (optional; agents degrade gracefully if unavailable)
# ---------------------------------------------------------------------------

mcp_context7 = _make_mcp(
    MCPServerHTTP,
    required_env="CONTEXT7_API_KEY",
    url="https://mcp.context7.com/mcp",
    headers={"CONTEXT7_API_KEY": os.getenv("CONTEXT7_API_KEY", "")},
    cache_tools_list=True,
)

mcp_sequential_thinking = _make_mcp(
    MCPServerStdio,
    required_cmd="docker",
    command="docker",
    args=["run", "--rm", "-i", "mcp/sequentialthinking"],
)

mcp_brave_search = _make_mcp(
    MCPServerStdio,
    required_env="BRAVE_API_KEY",
    required_cmd="docker",
    command="docker",
    args=["run", "-i", "--rm", "-e", "BRAVE_API_KEY", "docker.io/mcp/brave-search"],
    env={"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY", "")},
)

# MCP server exposing local SKILL.md files via skills_mcp (skills_list_skills / skills_get_skill).
mcp_skills = _make_mcp(
    MCPServerStdio,
    command=_python_command(),
    args=["-m", "src.mcp.skills_mcp"],
)

_TOOL_BUNDLES = {
    "none": [],
    "read_only": [file_read_tool, code_docs_tool],
    "validator_read": [file_read_tool, directory_read_tool, json_search_tool],
    "implementer_io": [file_read_tool, file_write_tool, directory_read_tool],
}

_MCP_BUNDLES = {
    "none": [],
    "research": [mcp_context7, mcp_brave_search, mcp_skills],
    "local_reasoning": [mcp_sequential_thinking, mcp_skills],
    "knowledge": [mcp_context7, mcp_skills],
}


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
    prepare_vision_runtime(context)
    vision_path = get_vision_path(context)
    return TextFileKnowledgeSource(file_paths=[vision_path])


def _vision_label(context: VisionContext = VisionContext.PROJECT) -> str:
    """Return the human-readable vision document name for prompts."""
    return _VISION_PATHS[context].name


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
    safe_namespace = namespace.strip("/") or "shared"
    storage_dir = (
        resolve_project_root()
        / ".crewai"
        / "memory"
        / context.value
        / safe_namespace
    )
    storage_dir.mkdir(parents=True, exist_ok=True)
    return Memory(storage=str(storage_dir))


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
