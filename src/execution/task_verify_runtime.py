from __future__ import annotations

from pathlib import Path
from typing import Any

from crewai import Agent, Crew, Task

from dialectic.agents import crew_memory, vision_knowledge, llm_simple
from dialectic.tools import directory_read_tool, file_read_tool
from dialectic.vision import VisionContext
from dialectic.yaml_config import (
    load_yaml_config,
    render_yaml_config,
    resolve_guardrail,
    resolve_output_schema,
)


_TASKS_CONFIG_PATH = Path(__file__).with_name("config") / "tasks_taskflow_verify.yaml"


def build_task_flow_verification_crew(
    *,
    task_id: str,
    task_title: str,
    task_description: str,
    acceptance_checks: list[str] | None,
    vision_context: VisionContext,
) -> Crew:
    task_templates = load_yaml_config(_TASKS_CONFIG_PATH)
    verify_agent = _build_agent()
    placeholders = {
        "task_id": task_id,
        "task_title": task_title,
        "task_description": task_description,
        "acceptance_checks_block": _render_acceptance_checks_block(acceptance_checks),
    }

    verify_task = _build_task(
        task_templates["verify_task_flow_implementation"],
        placeholders,
        verify_agent,
    )

    return Crew(
        agents=[verify_agent],
        tasks=[verify_task],
        verbose=True,
        memory=crew_memory(vision_context, "task_verify"),
        knowledge_sources=[vision_knowledge(vision_context)],
    )


def _render_acceptance_checks_block(acceptance_checks: list[str] | None) -> str:
    if not acceptance_checks:
        return ""

    checks_text = "\n".join(f"- {check}" for check in acceptance_checks)
    return f"\n\nACCEPTANCE CHECKS (verify each one):\n{checks_text}"


def _build_agent() -> Agent:
    return Agent(
        role="Independent Verifier",
        goal="Verify whether implementation artifacts exist in the codebase",
        backstory=(
            "You verify implementations by reading actual project files. "
            "Be objective: the artifact either exists or it does not."
        ),
        verbose=True,
        allow_delegation=False,
        reasoning=True,
        max_reasoning_attempts=2,
        llm=llm_simple,
        tools=[file_read_tool, directory_read_tool],
    )


def _build_task(template: dict[str, Any], placeholders: dict[str, Any], agent: Any) -> Task:
    config = dict(render_yaml_config(template, placeholders))
    output_schema = config.pop("output_schema", None)
    guardrail = config.pop("guardrail", None)
    if output_schema:
        config["output_pydantic"] = resolve_output_schema(output_schema)
    if guardrail:
        config["guardrail"] = resolve_guardrail(guardrail)
    config["agent"] = agent
    return Task(**config)