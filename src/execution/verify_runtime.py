"""Runtime builder for the standalone verification crew."""

# pylint: disable=duplicate-code

from __future__ import annotations

from pathlib import Path
from typing import Any

from crewai import Crew, Task

from dialectic.agents import create_validador_macro
from dialectic.crew_builder import build_sequential_crew_kwargs
from dialectic.knowledge import vision_knowledge
from dialectic.tools import file_read_tool, stack_validation_tool
from dialectic.vision import VisionContext
from dialectic.yaml_config import (
    load_yaml_config,
    render_yaml_config,
    resolve_output_schema,
)
from schemas import ImplementationTask


_TASKS_CONFIG_PATH = Path(__file__).with_name("config") / "tasks_verify.yaml"

_VERIFICATION_RESPONSE_RULES = (
    "Return ONLY valid JSON matching ValidationOutput with keys quality_score, "
    "consensus_reached, and final_validation_notes. Do not wrap the JSON in markdown. "
    "Do not include commentary before or after the JSON."
)

_VERIFY_AGENT_SUFFIX = (
    "You are operating in structured story-verification mode. Use file-reading and "
    "stack-validation tools only when necessary, do not use memory tools, and always "
    "return raw ValidationOutput JSON with no extra text."
)


def build_verification_crew(
    *,
    task: ImplementationTask,
    acceptance_criteria: list[str] | None,
    vision_context: VisionContext,
) -> Crew:
    """Build the single-task verification crew for a planned implementation task."""
    task_templates = load_yaml_config(_TASKS_CONFIG_PATH)
    verify_agent = create_validador_macro(vision_context)
    _configure_agent(verify_agent, [file_read_tool, stack_validation_tool])

    placeholders = {
        "task_id": task.id,
        "task_title": task.title,
        "task_description": task.description,
        "acceptance_criteria_block": _render_acceptance_criteria_block(
            acceptance_criteria
        ),
        "verification_response_rules": _VERIFICATION_RESPONSE_RULES,
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
            memory=None,
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


def _configure_agent(agent: Any, tools: list[Any]) -> None:
    """Assign tools and structured-mode settings to either dict-like or object-based agents."""
    if isinstance(agent, dict):
        agent["tools"] = tools
        backstory = agent.get("backstory", "")
        agent["backstory"] = f"{backstory} {_VERIFY_AGENT_SUFFIX}".strip()
        agent["reasoning"] = False
        return
    agent.tools = tools
    if hasattr(agent, "backstory"):
        agent.backstory = (
            f"{getattr(agent, 'backstory', '')} {_VERIFY_AGENT_SUFFIX}".strip()
        )
    if hasattr(agent, "reasoning"):
        agent.reasoning = False


def _build_task(
    template: dict[str, Any], placeholders: dict[str, Any], agent: Any
) -> Task:
    """Create the verification task from YAML configuration and placeholders."""
    config = dict(render_yaml_config(template, placeholders))
    output_schema = config.pop("output_schema", None)
    if output_schema:
        config["output_pydantic"] = resolve_output_schema(output_schema)
    config["agent"] = agent
    return Task(**config)
