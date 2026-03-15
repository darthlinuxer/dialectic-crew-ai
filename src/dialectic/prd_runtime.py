"""Crew construction helpers for the PRD dialectic flow."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

import crewai
from crewai import Crew, Task

from dialectic.agents import (
    create_critico_socratico,
    create_sintetizador,
    create_validador_macro,
    create_visionario,
)
from dialectic.crew_builder import (
    build_dialectic_sequential_crew,
    build_task_from_agent_mapping,
)
from dialectic.knowledge import _vision_label, _vision_path, crew_memory, vision_knowledge
from dialectic.vision import VisionContext
from dialectic.yaml_config import load_yaml_config


_TASKS_CONFIG_PATH = Path(__file__).with_name("config") / "tasks_prd.yaml"
Process = crewai.Process


def _prd_memory_namespace(feature_objective: str) -> str:
    normalized = feature_objective.strip() or "shared"
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"prd/{digest}"


def build_prd_crew(
    *,
    feature_objective: str,
    vision_context: VisionContext,
    retry_feedback_block: str,
    retry_feedback_sources: list[Any],
    memory_namespace: str | None = None,
) -> Crew:
    """Build the PRD dialectic crew for a single feature objective."""

    task_templates = load_yaml_config(_TASKS_CONFIG_PATH)
    placeholders = {
        "feature_objective": feature_objective,
        "vision_label": _vision_label(vision_context),
        "vision_path": _vision_path(vision_context),
        "retry_feedback_block": retry_feedback_block,
    }

    agents = _build_agents(vision_context)
    tasks = _build_prd_tasks(task_templates, placeholders, agents)
    knowledge_sources = [vision_knowledge(vision_context), *retry_feedback_sources]
    return build_dialectic_sequential_crew(
        crew_factory=Crew,
        agents_by_name=agents,
        thesis_agent_name="visionario",
        tasks=tasks,
        knowledge_sources=knowledge_sources,
        memory=crew_memory(
            vision_context,
            memory_namespace or _prd_memory_namespace(feature_objective),
        ),
        planning=False,
    )


def _disable_interactive_agent_io(agent: Any) -> Any:
    """Keep PRD agents focused on context + knowledge, not ad-hoc tool calls."""
    for attr in ("tools", "mcps", "mcp_servers"):
        if hasattr(agent, attr):
            setattr(agent, attr, [])
    return agent


def _build_agents(vision_context: VisionContext) -> dict[str, Any]:
    """Create fresh PRD agents for the requested vision context."""

    return {
        "visionario": _disable_interactive_agent_io(create_visionario(vision_context)),
        "critico_socratico": _disable_interactive_agent_io(
            create_critico_socratico(vision_context)
        ),
        "sintetizador": _disable_interactive_agent_io(create_sintetizador(vision_context)),
        "validador_macro": _disable_interactive_agent_io(create_validador_macro(vision_context)),
    }


def _build_prd_tasks(
    task_templates: dict[str, dict[str, Any]],
    placeholders: dict[str, Any],
    agents: Mapping[str, Any],
) -> list[Task]:
    """Build the ordered PRD thesis-to-validation task chain."""

    task_vision = build_task_from_agent_mapping(
        task_templates["prd_thesis"],
        placeholders,
        agents,
        task_factory=Task,
    )
    task_critica = build_task_from_agent_mapping(
        task_templates["prd_antithesis"],
        placeholders,
        agents,
        context=[task_vision],
        task_factory=Task,
    )
    task_sintese = build_task_from_agent_mapping(
        task_templates["prd_synthesis"],
        placeholders,
        agents,
        context=[task_vision, task_critica],
        task_factory=Task,
    )
    task_validacao = build_task_from_agent_mapping(
        task_templates["prd_validation"],
        placeholders,
        agents,
        context=[task_vision, task_critica, task_sintese],
        task_factory=Task,
    )
    return [task_vision, task_critica, task_sintese, task_validacao]
