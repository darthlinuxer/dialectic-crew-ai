"""Runtime builder for the standalone verification crew."""

# pylint: disable=duplicate-code

from __future__ import annotations

from pathlib import Path
from typing import Any

from crewai import Crew, Task

from dialectic.agents import create_validador_macro
from dialectic.crew_builder import build_sequential_crew_kwargs
from dialectic.knowledge import crew_memory, vision_knowledge
from dialectic.tools import file_read_tool, stack_validation_tool
from dialectic.vision import VisionContext
from dialectic.yaml_config import load_yaml_config, render_yaml_config, resolve_output_schema
from schemas import ImplementationTask


_TASKS_CONFIG_PATH = Path(__file__).with_name("config") / "tasks_verify.yaml"


def build_verification_crew(
    *,
    task: ImplementationTask,
    acceptance_criteria: list[str] | None,
    vision_context: VisionContext,
) -> Crew:
    """Build the single-task verification crew for a planned implementation task."""
    task_templates = load_yaml_config(_TASKS_CONFIG_PATH)
    verify_agent = create_validador_macro(vision_context)
    _assign_tools(verify_agent, [file_read_tool, stack_validation_tool])

    placeholders = {
        "task_id": task.id,
        "task_title": task.title,
        "task_description": task.description,
        "acceptance_criteria_block": _render_acceptance_criteria_block(acceptance_criteria),
    }

    verify_task = _build_task(
        task_templates["verify_single_task"],
        placeholders,
        verify_agent,
    )

    return Crew(
        agents=[verify_agent],
        **build_sequential_crew_kwargs(
            tasks=[verify_task],
            knowledge_sources=[vision_knowledge(vision_context)],
            memory=crew_memory(vision_context, "verify"),
        ),
    )


def _render_acceptance_criteria_block(acceptance_criteria: list[str] | None) -> str:
    """Render acceptance criteria text for the verifier prompt when criteria exist."""
    if not acceptance_criteria:
        return ""

    criteria_text = "\n".join(f"- {criterion}" for criterion in acceptance_criteria)
    return (
        "\n\nACCEPTANCE CRITERIA for the User Story "
        "(verify whether this task contributes to meeting them):\n"
        f"{criteria_text}"
    )


def _assign_tools(agent: Any, tools: list[Any]) -> None:
    """Assign a concrete tool list to either dict-like or object-based agents."""
    if isinstance(agent, dict):
        agent["tools"] = tools
        return
    agent.tools = tools


def _build_task(template: dict[str, Any], placeholders: dict[str, Any], agent: Any) -> Task:
    """Create the verification task from YAML configuration and placeholders."""
    config = dict(render_yaml_config(template, placeholders))
    output_schema = config.pop("output_schema", None)
    if output_schema:
        config["output_pydantic"] = resolve_output_schema(output_schema)
    config["agent"] = agent
    return Task(**config)
