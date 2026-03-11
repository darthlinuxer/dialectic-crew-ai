from __future__ import annotations

from pathlib import Path
from typing import Any

from crewai import Agent, Crew, Process, Task

from dialectic.agents import create_validador_macro
from dialectic.knowledge import _vision_label, crew_memory, vision_knowledge
from dialectic.llm import llm_complex
from dialectic.tools import directory_read_tool, file_read_tool, file_write_tool
from dialectic.vision import VisionContext
from dialectic.yaml_config import (
    load_yaml_config,
    render_yaml_config,
    resolve_guardrail,
    resolve_output_schema,
)


_TASKS_CONFIG_PATH = Path(__file__).with_name("config") / "tasks_taskflow_reimplement.yaml"


def build_task_flow_reimplementation_crew(
    *,
    task_id: str,
    task_title: str,
    task_description: str,
    failed_checks: list[str],
    verification_notes: str,
    dialectic_context: str,
    min_score: float,
    vision_context: VisionContext,
) -> Crew:
    task_templates = load_yaml_config(_TASKS_CONFIG_PATH)
    placeholders = {
        "task_id": task_id,
        "task_title": task_title,
        "task_description": task_description,
        "failed_checks": _render_failed_checks(failed_checks),
        "verification_notes": verification_notes[:2000],
        "dialectic_context": dialectic_context[:2000] or "N/A",
        "min_score": min_score,
        "vision_label": _vision_label(vision_context),
    }

    reimpl_agent = _build_agent()
    reval_agent = create_validador_macro(vision_context)

    task_fix = _build_task(
        task_templates["reimplement_task_fix"],
        placeholders,
        reimpl_agent,
    )
    task_revalidate = _build_task(
        task_templates["reimplement_task_validate"],
        placeholders,
        reval_agent,
        context=[task_fix],
    )

    return Crew(
        agents=[reimpl_agent, reval_agent],
        tasks=[task_fix, task_revalidate],
        process=Process.sequential,
        verbose=True,
        memory=crew_memory(vision_context, "task_reimplement"),
        knowledge_sources=[vision_knowledge(vision_context)],
    )


def _render_failed_checks(failed_checks: list[str]) -> str:
    if not failed_checks:
        return "N/A"
    return "\n".join(f"- {check}" for check in failed_checks)


def _build_agent() -> Agent:
    return Agent(
        role="Independent Implementer",
        goal="Fix failed implementation based on checks that did not pass",
        backstory=(
            "You are an implementer focused on fixing specific gaps. "
            "Read existing files, identify what is missing, and fix it."
        ),
        verbose=True,
        allow_delegation=False,
        reasoning=True,
        max_reasoning_attempts=2,
        llm=llm_complex,
        tools=[file_read_tool, file_write_tool, directory_read_tool],
    )


def _build_task(
    template: dict[str, Any],
    placeholders: dict[str, Any],
    agent: Any,
    **overrides: Any,
) -> Task:
    config = dict(render_yaml_config(template, placeholders))
    output_schema = config.pop("output_schema", None)
    guardrail = config.pop("guardrail", None)
    if output_schema:
        config["output_pydantic"] = resolve_output_schema(output_schema)
    if guardrail:
        config["guardrail"] = resolve_guardrail(guardrail)
    config["agent"] = agent
    config.update(overrides)
    return Task(**config)