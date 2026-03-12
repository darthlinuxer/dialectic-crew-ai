from pathlib import Path
from typing import Any

from crewai import Agent

from dialectic.llm import LLM_BY_TIER
from dialectic.knowledge import _vision_label, _vision_path
from dialectic.mcp_config import MCP_BUNDLES
from dialectic.tool_bundles import TOOL_BUNDLES
from dialectic.vision import VisionContext
from dialectic.yaml_config import load_yaml_config, render_yaml_config

_AGENTS_CONFIG_PATH = Path(__file__).with_name("config") / "agents.yaml"


def _get_agent_config(name: str) -> dict[str, Any]:
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
        "tools": _resolve_bundle(tool_bundle, TOOL_BUNDLES, "tool"),
    }
    mcps = _resolve_bundle(mcp_bundle, MCP_BUNDLES, "MCP")
    if mcps:
        kwargs["mcps"] = mcps
    return Agent(**kwargs)


def _build_agent(
    name: str,
    vision_context: VisionContext = VisionContext.PROJECT,
) -> Agent:
    config = render_yaml_config(
        _get_agent_config(name),
        {
            "vision_label": _vision_label(vision_context),
            "vision_path": _vision_path(vision_context),
        },
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
