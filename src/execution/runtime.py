from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from crewai import Crew, Process, Task

from dialectic.agents import (
    create_critico_socratico,
    create_implementer,
    create_sintetizador,
    create_validador_macro,
)
from dialectic.knowledge import _vision_label, crew_memory, vision_knowledge
from dialectic.llm import llm_planning
from dialectic.vision import VisionContext
from dialectic.yaml_config import (
    load_yaml_config,
    render_yaml_config,
    resolve_guardrail,
    resolve_output_schema,
)


_TASKS_CONFIG_PATH = Path(__file__).with_name("config") / "tasks_dialectic.yaml"


def build_task_dialectic_crew(
    *,
    task_id: str,
    task_title: str,
    task_description: str,
    context_str: str,
    min_score: float,
    vision_context: VisionContext,
    synthesis_for_retry: str | None,
    retry: int,
    max_retries: int,
) -> Crew:
    task_templates = load_yaml_config(_TASKS_CONFIG_PATH)
    vision_label = _vision_label(vision_context)
    tese_input = _render_tese_input(
        task_id=task_id,
        task_title=task_title,
        task_description=task_description,
        context_str=context_str,
        vision_label=vision_label,
        synthesis_for_retry=synthesis_for_retry,
        retry=retry,
        max_retries=max_retries,
    )
    placeholders = {
        "task_id": task_id,
        "task_title": task_title,
        "task_description": task_description,
        "context_str": context_str,
        "vision_label": vision_label,
        "min_score": min_score,
        "tese_input": tese_input,
    }

    impl = create_implementer(vision_context)
    crit = create_critico_socratico(vision_context)
    sint = create_sintetizador(vision_context)
    val = create_validador_macro(vision_context)
    agents = {
        "implementer": impl,
        "critico_socratico": crit,
        "sintetizador": sint,
        "validador_macro": val,
    }

    task_impl = _build_task(task_templates["execute_task_thesis"], placeholders, agents)
    task_critica = _build_task(
        task_templates["execute_task_antithesis"],
        placeholders,
        agents,
        context=[task_impl],
    )
    task_sintese = _build_task(
        task_templates["execute_task_synthesis"],
        placeholders,
        agents,
        context=[task_impl, task_critica],
    )
    task_val = _build_task(
        task_templates["execute_task_validation"],
        placeholders,
        agents,
        context=[task_impl, task_critica, task_sintese],
    )

    tasks = [task_impl, task_critica, task_sintese, task_val]
    return Crew(
        agents=[impl, crit, sint, val],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
        memory=crew_memory(vision_context, "task_dialectic"),
        planning=True,
        planning_llm=llm_planning,
        knowledge_sources=[vision_knowledge(vision_context)],
    )


def _render_tese_input(
    *,
    task_id: str,
    task_title: str,
    task_description: str,
    context_str: str,
    vision_label: str,
    synthesis_for_retry: str | None,
    retry: int,
    max_retries: int,
) -> str:
    if synthesis_for_retry is None:
        return f"""
TASK TO IMPLEMENT: {task_id} — {task_title}

{task_description}

CONTEXT:
{context_str}

Consult the system's macro vision ({vision_label} is available via your knowledge sources).
"""

    return f"""
RETRY {retry}/{max_retries} — Incorporate ALL refinements below.

TASK: {task_id} — {task_title}

{task_description}

Consult the system's macro vision ({vision_label} is available via your knowledge sources).

CRITIQUES AND REFINEMENTS:
{synthesis_for_retry[:3000]}

Re-implement incorporating these refinements.
"""


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