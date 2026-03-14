"""Crew construction helpers for the PRD dialectic flow."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from crewai import Crew, Process, Task

from dialectic.agents import (
    create_critico_socratico,
    create_sintetizador,
    create_validador_macro,
    create_visionario,
)
from dialectic.knowledge import _vision_label, _vision_path, crew_memory, vision_knowledge
from dialectic.vision import VisionContext
from dialectic.yaml_config import (
    load_yaml_config,
    render_yaml_config,
    resolve_guardrail,
    resolve_output_schema,
)


_TASKS_CONFIG_PATH = Path(__file__).with_name("config") / "tasks_prd.yaml"


def build_prd_crew(
    *,
    feature_objective: str,
    vision_context: VisionContext,
    retry_feedback_block: str,
    retry_feedback_sources: list[Any],
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
    return Crew(
        agents=[
            agents["visionario"],
            agents["critico_socratico"],
            agents["sintetizador"],
            agents["validador_macro"],
        ],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=crew_memory(vision_context, "prd"),
        planning=False,
        knowledge_sources=knowledge_sources,
    )


def _build_agents(vision_context: VisionContext) -> dict[str, Any]:
    """Create fresh PRD agents for the requested vision context."""

    return {
        "visionario": create_visionario(vision_context),
        "critico_socratico": create_critico_socratico(vision_context),
        "sintetizador": create_sintetizador(vision_context),
        "validador_macro": create_validador_macro(vision_context),
    }


def _build_prd_tasks(
    task_templates: dict[str, dict[str, Any]],
    placeholders: dict[str, Any],
    agents: Mapping[str, Any],
) -> list[Task]:
    """Build the ordered PRD thesis-to-validation task chain."""

    task_vision = _build_task(task_templates["prd_thesis"], placeholders, agents)
    task_critica = _build_task(
        task_templates["prd_antithesis"],
        placeholders,
        agents,
        context=[task_vision],
    )
    task_sintese = _build_task(
        task_templates["prd_synthesis"],
        placeholders,
        agents,
        context=[task_vision, task_critica],
    )
    task_validacao = _build_task(
        task_templates["prd_validation"],
        placeholders,
        agents,
        context=[task_vision, task_critica, task_sintese],
    )
    return [task_vision, task_critica, task_sintese, task_validacao]


def _build_task(
    template: dict[str, Any],
    placeholders: dict[str, Any],
    agents: Mapping[str, Any],
    **overrides: Any,
) -> Task:
    config = dict(render_yaml_config(template, placeholders))
    agent_name = config.pop("agent")
    output_schema = config.pop("output_schema", None)
    guardrail = config.pop("guardrail", None)
    if output_schema:
        config["output_pydantic"] = resolve_output_schema(output_schema)
    if guardrail:
        config["guardrail"] = resolve_guardrail(guardrail)
    config["agent"] = agents[agent_name]
    config.update(overrides)
    return Task(**config)
