"""Build the per-task dialectic execution crew and its runtime prompts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from crewai import Crew, Task

from dialectic.agents import (
    _get_agent_config,
    build_agent_from_config,
    create_critico_socratico,
    create_sintetizador,
    create_validador_macro,
)
from dialectic.crew_builder import (
    build_dialectic_sequential_crew,
    build_task_from_agent_mapping,
)
from dialectic.knowledge import (
    _vision_label,
    _vision_path,
    crew_memory,
    style_guide_knowledge,
    vision_knowledge,
)
from dialectic.llm import llm_planning
from dialectic.vision import VisionContext, normalize_vision_context
from dialectic.yaml_config import load_yaml_config, render_yaml_config


_TASKS_CONFIG_PATH = Path(__file__).with_name("config") / "tasks_dialectic.yaml"
_FINAL_TEXT_RESPONSE_RULES = """
Final response rules:
- Return only the completed plain-text answer for this task.
- Never return raw tool-call objects, tool arguments, JSON wrappers, or tool metadata.
- If you use tools, execute them first and then reply with the finished textual result only.
""".strip()
_PLAIN_TEXT_IMPLEMENTATION_EXPECTED_OUTPUT = (
    "Plain-text answer only describing what was implemented and which files "
    "were created or modified"
)
_PLAIN_TEXT_CRITIQUE_EXPECTED_OUTPUT = (
    "Plain-text answer only containing a detailed critique of the implementation"
)
_PLAIN_TEXT_SYNTHESIS_EXPECTED_OUTPUT = (
    "Plain-text answer only containing the refined synthesis and retry instructions"
)
_TASK_EXECUTION_IMPLEMENTER_SUFFIX = """

Execution-mode constraints:
- Use local project tools first; do not rely on research MCP tools during task execution.
- Never finish with a tool call, tool arguments, or raw tool output.
- After any file/tool actions, always produce a concise plain-text completion summary.
""".strip()


def build_task_execution_implementer(vision_context: VisionContext) -> Any:
    """Create a task-scoped implementer agent tuned for live execution reliability."""
    config = dict(
        render_yaml_config(
            _get_agent_config("implementer"),
            {
                "vision_label": _vision_label(vision_context),
                "vision_path": _vision_path(vision_context),
            },
        )
    )
    config["mcp_bundle"] = "none"
    config["backstory"] = (
        f"{config['backstory'].rstrip()}\n\n{_TASK_EXECUTION_IMPLEMENTER_SUFFIX}"
    )
    return build_agent_from_config(config)


def _build_runtime_agents(vision_context: VisionContext) -> dict[str, Any]:
    """Create the agent set used by the task dialectic execution crew."""
    return {
        "implementer": build_task_execution_implementer(vision_context),
        "critico_socratico": create_critico_socratico(vision_context),
        "sintetizador": create_sintetizador(vision_context),
        "validador_macro": create_validador_macro(vision_context),
    }


def _build_runtime_placeholders(
    *,
    task_metadata: Mapping[str, str],
    min_score: float,
    vision_context: VisionContext,
    retry_context: Mapping[str, Any],
) -> dict[str, Any]:
    """Render the template placeholders shared by the execution tasks."""
    vision_label = _vision_label(vision_context)
    vision_path = _vision_path(vision_context)
    vision_file_ref = f"#file:{vision_label}"
    placeholders: dict[str, Any] = {
        **task_metadata,
        "vision_label": vision_label,
        "vision_path": vision_path,
        "vision_file_ref": vision_file_ref,
        "min_score": min_score,
        "final_text_response_rules": _FINAL_TEXT_RESPONSE_RULES,
        "plain_text_implementation_expected_output": _PLAIN_TEXT_IMPLEMENTATION_EXPECTED_OUTPUT,
        "plain_text_critique_expected_output": _PLAIN_TEXT_CRITIQUE_EXPECTED_OUTPUT,
        "plain_text_synthesis_expected_output": _PLAIN_TEXT_SYNTHESIS_EXPECTED_OUTPUT,
    }
    placeholders["tese_input"] = _render_tese_input(
        placeholders=placeholders,
        synthesis_for_retry=retry_context["synthesis_for_retry"],
        retry=retry_context["retry"],
        max_retries=retry_context["max_retries"],
    )
    return placeholders


def _build_runtime_tasks(
    task_templates: Mapping[str, dict[str, Any]],
    placeholders: dict[str, Any],
    agents: Mapping[str, Any],
) -> list[Task]:
    """Build the sequential thesis/antithesis/synthesis/validation tasks."""
    task_impl = build_task_from_agent_mapping(
        task_templates["execute_task_thesis"],
        placeholders,
        agents,
        task_factory=Task,
    )
    task_critica = build_task_from_agent_mapping(
        task_templates["execute_task_antithesis"],
        placeholders,
        agents,
        context=[task_impl],
        task_factory=Task,
    )
    task_sintese = build_task_from_agent_mapping(
        task_templates["execute_task_synthesis"],
        placeholders,
        agents,
        context=[task_impl, task_critica],
        task_factory=Task,
    )
    task_val = build_task_from_agent_mapping(
        task_templates["execute_task_validation"],
        placeholders,
        agents,
        context=[task_impl, task_critica, task_sintese],
        task_factory=Task,
    )
    return [task_impl, task_critica, task_sintese, task_val]


def _build_runtime_knowledge_sources(vision_context: VisionContext) -> list[Any]:
    """Return the knowledge sources required by the execution crew."""
    knowledge_sources = [vision_knowledge(vision_context)]
    if vision_context is VisionContext.SELF:
        knowledge_sources.extend(style_guide_knowledge())
    return knowledge_sources


# pylint: disable=too-many-arguments,too-many-locals
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
    """Build the dialectic CrewAI runtime used to execute a single task."""
    task_templates = load_yaml_config(_TASKS_CONFIG_PATH)
    normalized_context = normalize_vision_context(vision_context)
    task_metadata = {
        "task_id": task_id,
        "task_title": task_title,
        "task_description": task_description,
        "context_str": context_str,
    }
    retry_context = {
        "synthesis_for_retry": synthesis_for_retry,
        "retry": retry,
        "max_retries": max_retries,
    }
    placeholders = _build_runtime_placeholders(
        task_metadata=task_metadata,
        min_score=min_score,
        vision_context=normalized_context,
        retry_context=retry_context,
    )
    agents = _build_runtime_agents(normalized_context)
    tasks = _build_runtime_tasks(task_templates, placeholders, agents)
    knowledge_sources = _build_runtime_knowledge_sources(normalized_context)
    return build_dialectic_sequential_crew(
        crew_factory=Crew,
        agents_by_name=agents,
        thesis_agent_name="implementer",
        tasks=tasks,
        knowledge_sources=knowledge_sources,
        memory=crew_memory(normalized_context, "task_dialectic"),
        planning=True,
        planning_llm=llm_planning,
    )


def _render_tese_input(
    *,
    placeholders: Mapping[str, Any],
    synthesis_for_retry: str | None,
    retry: int,
    max_retries: int,
) -> str:
    """Render the thesis-task input block used by the execution crew."""
    task_id = str(placeholders["task_id"])
    task_title = str(placeholders["task_title"])
    task_description = str(placeholders["task_description"])
    context_str = str(placeholders["context_str"])
    vision_path = str(placeholders["vision_path"])
    vision_file_ref = str(placeholders["vision_file_ref"])
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

{_FINAL_TEXT_RESPONSE_RULES}

Consult the system's anti-drift file {vision_file_ref} at exact path `{vision_path}`.
Treat the knowledge-source content for `{vision_path}` as authoritative.
"""

    return f"""
RETRY {retry}/{max_retries} — Incorporate ALL refinements below.

TASK: {task_id} — {task_title}

{task_description}

{integration_done_block}

{_FINAL_TEXT_RESPONSE_RULES}

Consult the system's anti-drift file {vision_file_ref} at exact path `{vision_path}`.
Treat the knowledge-source content for `{vision_path}` as authoritative.

CRITIQUES AND REFINEMENTS:
{synthesis_for_retry[:3000]}

Re-implement incorporating these refinements.
"""
