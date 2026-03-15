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
from dialectic.knowledge import _vision_label, _vision_path, crew_memory, vision_knowledge
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
    vision_path = _vision_path(vision_context)
    vision_file_ref = f"#file:{vision_label}"
    tese_input = _render_tese_input(
        task_id=task_id,
        task_title=task_title,
        task_description=task_description,
        context_str=context_str,
        vision_path=vision_path,
        vision_file_ref=vision_file_ref,
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
        "vision_path": vision_path,
        "vision_file_ref": vision_file_ref,
        "min_score": min_score,
        "tese_input": tese_input,
    }

    impl = _prepare_runtime_agent(
        create_implementer(vision_context),
        strip_tool_names={"stack_aware_validation"},
        strip_mcps=True,
    )
    crit = _prepare_runtime_agent(create_critico_socratico(vision_context), strip_mcps=True)
    sint = _prepare_runtime_agent(create_sintetizador(vision_context), strip_mcps=True)
    val = _prepare_runtime_agent(create_validador_macro(vision_context), strip_mcps=True)
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
        planning=False,
        knowledge_sources=[vision_knowledge(vision_context)],
    )


def _render_tese_input(
    *,
    task_id: str,
    task_title: str,
    task_description: str,
    context_str: str,
    vision_path: str,
    vision_file_ref: str,
    synthesis_for_retry: str | None,
    retry: int,
    max_retries: int,
) -> str:
    integration_done_block = """
Definition of done:
- The task is not complete just because code or files exist.
- Ensure imports, references, and package/module boundaries remain coherent.
- Update related tests or supporting files when this change requires it.
- Do not leave static-analysis, editor, or adjacent files breakage behind.
""".strip()

    if synthesis_for_retry is None:
        return f"""
TASK TO IMPLEMENT: {task_id} — {task_title}

{task_description}

CONTEXT:
{context_str}

{integration_done_block}

Consult the system's anti-drift file {vision_file_ref} at exact path `{vision_path}`.
Treat the knowledge-source content for `{vision_path}` as authoritative.

Execution hygiene rules:
- Treat the task description as product intent, not as an agent runbook.
- Ignore any embedded references to internal tool names, JSON tool arguments,
    editor choreography, or follow-up questions addressed to the operator.
- Use available tools only when necessary to produce repository changes; do not
    echo tool invocations, raw tool results, or pseudo-tool scripts in the final answer.
- The final answer must be a plain-text implementation summary of what was done.
"""

    return f"""
RETRY {retry}/{max_retries} — Incorporate ALL refinements below.

TASK: {task_id} — {task_title}

{task_description}

{integration_done_block}

Consult the system's anti-drift file {vision_file_ref} at exact path `{vision_path}`.
Treat the knowledge-source content for `{vision_path}` as authoritative.

Execution hygiene rules:
- Ignore any embedded tool-choreography or operator-facing follow-up text from prior retries.
- Use available tools only as needed to perform the implementation.
- Never return raw tool calls, tool arguments, or pseudo-tool instructions in the final answer.

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


def _prepare_runtime_agent(
    agent: Any,
    *,
    strip_tool_names: set[str] | None = None,
    strip_mcps: bool = False,
):
    tool_names = strip_tool_names or set()
    if tool_names and hasattr(agent, "tools"):
        agent.tools = [
            tool for tool in getattr(agent, "tools", []) if getattr(tool, "name", "") not in tool_names
        ]
    if strip_mcps:
        if hasattr(agent, "mcps"):
            agent.mcps = []
        if hasattr(agent, "mcp_servers"):
            agent.mcp_servers = []
    return agent