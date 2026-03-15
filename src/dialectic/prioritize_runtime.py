from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from crewai import Agent, Crew, Process, Task

from dialectic.crew_verbose_config import get_output_log_file, is_verbose
from dialectic.knowledge import _vision_label, vision_knowledge
from dialectic.llm import llm_simple
from dialectic.vision import VisionContext
from dialectic.yaml_config import (
    load_yaml_config,
    render_yaml_config,
    resolve_guardrail,
    resolve_output_schema,
)


_AGENTS_CONFIG_PATH = Path(__file__).with_name("config") / "agents_prioritize.yaml"
_TASKS_CONFIG_PATH = Path(__file__).with_name("config") / "tasks_prioritize.yaml"


def build_prioritization_crew(*, opp_text: str, opp_ids_str: str, vision_context: VisionContext) -> Crew:
    vision_label = _vision_label(vision_context)
    placeholders = {
        "opp_text": opp_text,
        "opp_ids_str": opp_ids_str,
        "vision_label": vision_label,
    }
    agent_templates = load_yaml_config(_AGENTS_CONFIG_PATH)
    task_templates = load_yaml_config(_TASKS_CONFIG_PATH)

    analyst = _build_agent(agent_templates["prioritize_analyst"], placeholders)
    critic = _build_agent(agent_templates["prioritize_critic"], placeholders)
    ranker = _build_agent(agent_templates["prioritize_ranker"], placeholders)
    agents = {
        "prioritize_analyst": analyst,
        "prioritize_critic": critic,
        "prioritize_ranker": ranker,
    }

    task_analysis = _build_task(task_templates["prioritize_analysis"], placeholders, agents)
    task_critique = _build_task(
        task_templates["prioritize_critique"],
        placeholders,
        agents,
        context=[task_analysis],
    )
    task_rank = _build_task(
        task_templates["prioritize_rank"],
        placeholders,
        agents,
        context=[task_analysis, task_critique],
    )

    tasks = [task_analysis, task_critique, task_rank]
    return Crew(
        agents=[analyst, critic, ranker],
        tasks=tasks,
        process=Process.sequential,
        verbose=is_verbose(),
        output_log_file=get_output_log_file(),
        knowledge_sources=[vision_knowledge(vision_context)],
    )


def _build_agent(template: dict[str, Any], placeholders: dict[str, Any]) -> Agent:
    config = dict(render_yaml_config(template, placeholders))
    config["llm"] = llm_simple
    return Agent(**config)


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