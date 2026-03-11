from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from crewai import Crew, Process, Task
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource

from dialectic.agents import (
    create_critico_socratico,
    create_sintetizador,
    create_validador_macro,
    create_visionario,
)
from dialectic.knowledge import _vision_label, crew_memory, vision_knowledge
from dialectic.llm import llm_planning
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
    retry_feedback_sources: list[StringKnowledgeSource],
) -> Crew:
    task_templates = load_yaml_config(_TASKS_CONFIG_PATH)
    placeholders = {
        "feature_objective": feature_objective,
        "vision_label": _vision_label(vision_context),
        "retry_feedback_block": retry_feedback_block,
    }

    vis = create_visionario(vision_context)
    crit = create_critico_socratico(vision_context)
    sint = create_sintetizador(vision_context)
    val = create_validador_macro(vision_context)
    agents = {
        "visionario": vis,
        "critico_socratico": crit,
        "sintetizador": sint,
        "validador_macro": val,
    }

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

    tasks = [task_vision, task_critica, task_sintese, task_validacao]
    knowledge_sources = [vision_knowledge(vision_context), *retry_feedback_sources]
    return Crew(
        agents=[vis, crit, sint, val],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=crew_memory(vision_context, "prd"),
        planning=True,
        planning_llm=llm_planning,
        knowledge_sources=knowledge_sources,
    )


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