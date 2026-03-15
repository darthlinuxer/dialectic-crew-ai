"""Build the dialectic prioritization crew for improvement opportunities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import crewai
from crewai import Agent, Crew, Task

from dialectic.crew_builder import (
    build_sequential_crew,
    build_task_from_agent_mapping,
)
from dialectic.knowledge import _vision_label, vision_knowledge
from dialectic.llm import llm_simple
from dialectic.vision import VisionContext
from dialectic.yaml_config import load_yaml_config, render_yaml_config


_AGENTS_CONFIG_PATH = Path(__file__).with_name("config") / "agents_prioritize.yaml"
_TASKS_CONFIG_PATH = Path(__file__).with_name("config") / "tasks_prioritize.yaml"
Process = crewai.Process


def build_prioritization_crew(
    *,
    opp_text: str,
    opp_ids_str: str,
    vision_context: VisionContext,
) -> Crew:
    """Build the analyst/critic/ranker crew used for opportunity prioritization."""
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

    task_analysis = build_task_from_agent_mapping(
        task_templates["prioritize_analysis"],
        placeholders,
        agents,
        task_factory=Task,
    )
    task_critique = build_task_from_agent_mapping(
        task_templates["prioritize_critique"],
        placeholders,
        agents,
        context=[task_analysis],
        task_factory=Task,
    )
    task_rank = build_task_from_agent_mapping(
        task_templates["prioritize_rank"],
        placeholders,
        agents,
        context=[task_analysis, task_critique],
        task_factory=Task,
    )

    tasks = [task_analysis, task_critique, task_rank]
    return build_sequential_crew(
        crew_factory=Crew,
        agents=[analyst, critic, ranker],
        tasks=tasks,
        knowledge_sources=[vision_knowledge(vision_context)],
    )


def _build_agent(template: dict[str, Any], placeholders: dict[str, Any]) -> Agent:
    config = dict(render_yaml_config(template, placeholders))
    config["llm"] = llm_simple
    return Agent(**config)
