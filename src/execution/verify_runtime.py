from __future__ import annotations

from pathlib import Path
from typing import Any

from crewai import Crew, Task

from dialectic.agents import create_validador_macro
from dialectic.crew_verbose_config import get_output_log_file, is_verbose
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
        tasks=[verify_task],
        verbose=is_verbose(),
        output_log_file=get_output_log_file(),
        memory=crew_memory(vision_context, "verify"),
        knowledge_sources=[vision_knowledge(vision_context)],
    )


def _render_acceptance_criteria_block(acceptance_criteria: list[str] | None) -> str:
    if not acceptance_criteria:
        return ""

    criteria_text = "\n".join(f"- {criterion}" for criterion in acceptance_criteria)
    return (
        "\n\nACCEPTANCE CRITERIA for the User Story "
        "(verify whether this task contributes to meeting them):\n"
        f"{criteria_text}"
    )


def _assign_tools(agent: Any, tools: list[Any]) -> None:
    if isinstance(agent, dict):
        agent["tools"] = tools
        return
    agent.tools = tools


def _build_task(template: dict[str, Any], placeholders: dict[str, Any], agent: Any) -> Task:
    config = dict(render_yaml_config(template, placeholders))
    output_schema = config.pop("output_schema", None)
    if output_schema:
        config["output_pydantic"] = resolve_output_schema(output_schema)
    config["agent"] = agent
    return Task(**config)