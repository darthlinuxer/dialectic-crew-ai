from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from crewai import Crew, Process, Task

from dialectic.agents import build_agent_from_config
from dialectic.knowledge import _vision_label, _vision_path, crew_memory, vision_knowledge
from dialectic.yaml_config import (
    load_yaml_config,
    render_yaml_config,
    resolve_guardrail,
    resolve_output_schema,
)
from dialectic.vision import VisionContext


_AGENTS_CONFIG_PATH = Path(__file__).with_name("config") / "agents.yaml"
_TASKS_CONFIG_PATH = Path(__file__).with_name("config") / "tasks.yaml"


def build_planning_crew(
    *,
    feature_context: str,
    us,
    us_context: str,
    vision_context: VisionContext,
    min_plan_score: float,
    retry_feedback_block: str = "",
    retry_feedback_sources: list[Any] | None = None,
) -> Crew:
    agent_templates = load_yaml_config(_AGENTS_CONFIG_PATH)
    task_templates = load_yaml_config(_TASKS_CONFIG_PATH)
    placeholders = {
        "feature_context": feature_context,
        "us_context": us_context,
        "us_id": us.id,
        "us_title": us.title,
        "vision_label": _vision_label(vision_context),
        "vision_path": _vision_path(vision_context),
        "min_plan_score": min_plan_score,
        "retry_feedback_block": retry_feedback_block,
    }

    vis = _build_agent(agent_templates["planning_visionary"], placeholders)
    crit = _build_agent(agent_templates["planning_critic"], placeholders)
    sint = _build_agent(agent_templates["planning_synthesizer"], placeholders)
    val = _build_agent(agent_templates["planning_validator"], placeholders)
    agents = {
        "planning_visionary": vis,
        "planning_critic": crit,
        "planning_synthesizer": sint,
        "planning_validator": val,
    }

    task_tese = _build_task(task_templates["thesis_plan"], placeholders, agents)
    task_antitese = _build_task(
        task_templates["antithesis_plan"],
        placeholders,
        agents,
        context=[task_tese],
    )
    task_sintese = _build_task(
        task_templates["synthesis_plan"],
        placeholders,
        agents,
        context=[task_tese, task_antitese],
    )
    task_validacao = _build_task(
        task_templates["validation_plan"],
        placeholders,
        agents,
        context=[task_tese, task_antitese, task_sintese],
    )

    tasks = [task_tese, task_antitese, task_sintese, task_validacao]
    return Crew(
        agents=[vis, crit, sint, val],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=crew_memory(vision_context, "planning"),
        planning=False,
        knowledge_sources=[vision_knowledge(vision_context), *(retry_feedback_sources or [])],
    )


def _build_agent(template: dict[str, Any], placeholders: dict[str, Any]):
    config = render_yaml_config(template, placeholders)
    return build_agent_from_config(config)


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