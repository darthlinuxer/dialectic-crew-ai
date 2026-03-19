"""Build the user-story planning crew and its dialectic task chain."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from crewai import Crew, Task

from dialectic.agents import build_agent_from_config
from dialectic.crew_builder import (
    build_named_sequential_crew,
    build_task_from_agent_mapping,
)
from dialectic.knowledge import (
    _vision_label,
    _vision_path,
    crew_memory,
    vision_knowledge,
)
from dialectic.llm import llm_planning
from dialectic.yaml_config import load_yaml_config, render_yaml_config
from dialectic.vision import VisionContext


_AGENTS_CONFIG_PATH = Path(__file__).with_name("config") / "agents.yaml"
_TASKS_CONFIG_PATH = Path(__file__).with_name("config") / "tasks.yaml"


def _disable_interactive_agent_io(agent: Any) -> Any:
    """Keep planning agents focused on context + knowledge, not ad-hoc tool calls."""
    for attr in ("tools", "mcps", "mcp_servers"):
        if hasattr(agent, attr):
            setattr(agent, attr, [])
    return agent


# pylint: disable=too-many-arguments
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
    """Build the dialectic planning crew for a single user story."""
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

    agents = _build_planning_agents(agent_templates, placeholders)
    tasks = _build_planning_tasks(task_templates, placeholders, agents)
    return build_named_sequential_crew(
        crew_factory=Crew,
        agents_by_name=agents,
        agent_names=(
            "planning_visionary",
            "planning_critic",
            "planning_synthesizer",
            "planning_validator",
        ),
        tasks=tasks,
        knowledge_sources=[
            vision_knowledge(vision_context),
            *(retry_feedback_sources or []),
        ],
        memory=crew_memory(vision_context, "planning"),
        planning=True,
        planning_llm=llm_planning,
    )


def _build_planning_agents(
    agent_templates: Mapping[str, dict[str, Any]],
    placeholders: dict[str, Any],
) -> dict[str, Any]:
    """Create and sanitize the planning crew agents in execution order."""
    return {
        "planning_visionary": _disable_interactive_agent_io(
            _build_agent(agent_templates["planning_visionary"], placeholders)
        ),
        "planning_critic": _disable_interactive_agent_io(
            _build_agent(agent_templates["planning_critic"], placeholders)
        ),
        "planning_synthesizer": _disable_interactive_agent_io(
            _build_agent(agent_templates["planning_synthesizer"], placeholders)
        ),
        "planning_validator": _disable_interactive_agent_io(
            _build_agent(agent_templates["planning_validator"], placeholders)
        ),
    }


def _build_planning_tasks(
    task_templates: Mapping[str, dict[str, Any]],
    placeholders: dict[str, Any],
    agents: Mapping[str, Any],
) -> list[Task]:
    """Build the ordered planning thesis-to-validation task chain."""
    task_tese = build_task_from_agent_mapping(
        task_templates["thesis_plan"],
        placeholders,
        agents,
        task_factory=Task,
    )
    task_antitese = build_task_from_agent_mapping(
        task_templates["antithesis_plan"],
        placeholders,
        agents,
        context=[task_tese],
        task_factory=Task,
    )
    task_sintese = build_task_from_agent_mapping(
        task_templates["synthesis_plan"],
        placeholders,
        agents,
        context=[task_tese, task_antitese],
        task_factory=Task,
    )
    task_validacao = build_task_from_agent_mapping(
        task_templates["validation_plan"],
        placeholders,
        agents,
        context=[task_tese, task_antitese, task_sintese],
        task_factory=Task,
    )
    return [task_tese, task_antitese, task_sintese, task_validacao]


def _build_agent(template: dict[str, Any], placeholders: dict[str, Any]):
    """Render and instantiate a planning agent from its YAML template."""
    config = render_yaml_config(template, placeholders)
    return build_agent_from_config(config)
