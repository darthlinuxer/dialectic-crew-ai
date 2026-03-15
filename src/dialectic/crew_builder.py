"""Shared helpers for constructing CrewAI tasks and sequential crews."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping

from crewai import Process, Task

from dialectic.crew_log_summarizer import get_step_summarizer_callback
from dialectic.crew_verbose_config import get_output_log_file, is_verbose
from dialectic.yaml_config import render_yaml_config, resolve_guardrail, resolve_output_schema


def build_task_from_agent_mapping(
    template: dict[str, Any],
    placeholders: Mapping[str, Any],
    agents: Mapping[str, Any],
    *,
    context: list[Any] | None = None,
    task_factory: type[Task] = Task,
) -> Task:
    """Build a Task whose agent is resolved from an agent-name mapping."""
    config = dict(render_yaml_config(template, dict(placeholders)))
    agent_name = config.pop("agent")
    output_schema = config.pop("output_schema", None)
    guardrail = config.pop("guardrail", None)
    if output_schema:
        config["output_pydantic"] = resolve_output_schema(output_schema)
    if guardrail:
        config["guardrail"] = resolve_guardrail(guardrail)
    config["agent"] = agents[agent_name]
    if context is not None:
        config["context"] = context
    return task_factory(**config)


def build_task_from_agent(
    template: dict[str, Any],
    placeholders: Mapping[str, Any],
    agent: Any,
    *,
    context: list[Any] | None = None,
    task_factory: type[Task] = Task,
) -> Task:
    """Build a Task bound to a single preselected agent instance."""
    config = dict(render_yaml_config(template, dict(placeholders)))
    output_schema = config.pop("output_schema", None)
    guardrail = config.pop("guardrail", None)
    if output_schema:
        config["output_pydantic"] = resolve_output_schema(output_schema)
    if guardrail:
        config["guardrail"] = resolve_guardrail(guardrail)
    config["agent"] = agent
    if context is not None:
        config["context"] = context
    return task_factory(**config)


def build_sequential_crew_kwargs(
    *,
    tasks: list[Any],
    knowledge_sources: list[Any],
    memory: Any | None = None,
    planning: bool | None = None,
    planning_llm: Any | None = None,
) -> dict[str, Any]:
    """Return the shared kwargs used by the repo's sequential Crew builders."""
    kwargs: dict[str, Any] = {
        "tasks": tasks,
        "process": Process.sequential,
        "verbose": is_verbose(),
        "output_log_file": get_output_log_file(),
        "step_callback": get_step_summarizer_callback(),
        "knowledge_sources": knowledge_sources,
    }
    if memory is not None:
        kwargs["memory"] = memory
    if planning is not None:
        kwargs["planning"] = planning
    if planning_llm is not None:
        kwargs["planning_llm"] = planning_llm
    return kwargs


def build_agent_list(agents: Mapping[str, Any], *agent_names: str) -> list[Any]:
    """Return agents in a deterministic order from a name-to-agent mapping."""
    return [agents[name] for name in agent_names]


# pylint: disable=too-many-arguments
def build_named_sequential_crew(
    *,
    crew_factory: Any,
    agents_by_name: Mapping[str, Any],
    agent_names: Sequence[str],
    tasks: list[Any],
    knowledge_sources: list[Any],
    memory: Any | None = None,
    planning: bool | None = None,
    planning_llm: Any | None = None,
) -> Any:
    """Instantiate a sequential crew from an ordered agent-name sequence."""
    return build_sequential_crew(
        crew_factory=crew_factory,
        agents=build_agent_list(agents_by_name, *agent_names),
        tasks=tasks,
        knowledge_sources=knowledge_sources,
        memory=memory,
        planning=planning,
        planning_llm=planning_llm,
    )


# pylint: disable=too-many-arguments
def build_dialectic_sequential_crew(
    *,
    crew_factory: Any,
    agents_by_name: Mapping[str, Any],
    thesis_agent_name: str,
    tasks: list[Any],
    knowledge_sources: list[Any],
    memory: Any | None = None,
    planning: bool | None = None,
    planning_llm: Any | None = None,
) -> Any:
    """Instantiate the standard thesis/critique/synthesis/validation crew."""
    return build_named_sequential_crew(
        crew_factory=crew_factory,
        agents_by_name=agents_by_name,
        agent_names=(
            thesis_agent_name,
            "critico_socratico",
            "sintetizador",
            "validador_macro",
        ),
        tasks=tasks,
        knowledge_sources=knowledge_sources,
        memory=memory,
        planning=planning,
        planning_llm=planning_llm,
    )


# pylint: disable=too-many-arguments
def build_sequential_crew(
    *,
    crew_factory: Any,
    agents: list[Any],
    tasks: list[Any],
    knowledge_sources: list[Any],
    memory: Any | None = None,
    planning: bool | None = None,
    planning_llm: Any | None = None,
) -> Any:
    """Instantiate a sequential crew using the repository's shared defaults."""
    return crew_factory(
        agents=agents,
        **build_sequential_crew_kwargs(
            tasks=tasks,
            knowledge_sources=knowledge_sources,
            memory=memory,
            planning=planning,
            planning_llm=planning_llm,
        ),
    )
