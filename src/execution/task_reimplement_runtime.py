"""Build the task reimplementation crew used after verification failures."""

from __future__ import annotations

from pathlib import Path
from crewai import Agent, Crew, Task

from dialectic.agents import create_validador_macro
from dialectic.crew_builder import build_sequential_crew, build_task_from_agent
from dialectic.crew_verbose_config import is_verbose
from dialectic.knowledge import (
    _vision_label,
    _vision_path,
    vision_knowledge,
)
from dialectic.llm import llm_complex
from dialectic.vision import VisionContext
from dialectic.yaml_config import load_yaml_config


_TASKS_CONFIG_PATH = (
    Path(__file__).with_name("config") / "tasks_taskflow_reimplement.yaml"
)


_FILE_SECTION_RESPONSE_RULES = (
    "Return plain text only. Do not call tools. After the short summary, emit one or more "
    "complete file sections using this exact format:\n"
    "--- relative/path/to/file.ext ---\n"
    "<full final file content>\n"
    "Repeat for every file that must change. If no file changes are needed, write exactly NO_FILE_CHANGES."
)

_TASK_REIMPLEMENTER_SUFFIX = (
    "You are operating in a text-first repair mode. Do not use file, directory, memory, or validation tools. "
    "Do not reread the anti-drift vision file via tools; rely on the injected knowledge source and prompt context. "
    "Produce a concise root-cause summary followed by complete file sections in the required format so the runtime "
    "can materialize the repair safely."
)


# pylint: disable=too-many-arguments
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
    """Build the repair-and-revalidate crew for a failed implementation task."""
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
        "vision_path": _vision_path(vision_context),
        "vision_file_ref": f"#file:{_vision_label(vision_context)}",
        "file_section_rules": _FILE_SECTION_RESPONSE_RULES,
    }

    reimpl_agent = _build_agent()
    reval_agent = create_validador_macro(vision_context)

    task_fix = build_task_from_agent(
        task_templates["reimplement_task_fix"],
        placeholders,
        reimpl_agent,
        task_factory=Task,
    )
    task_revalidate = build_task_from_agent(
        task_templates["reimplement_task_validate"],
        placeholders,
        reval_agent,
        context=[task_fix],
        task_factory=Task,
    )

    return build_sequential_crew(
        crew_factory=Crew,
        agents=[reimpl_agent, reval_agent],
        tasks=[task_fix, task_revalidate],
        knowledge_sources=[vision_knowledge(vision_context)],
        memory=None,
    )


def _render_failed_checks(failed_checks: list[str]) -> str:
    """Render failed verification checks for inclusion in the repair prompt."""
    if not failed_checks:
        return "N/A"
    return "\n".join(f"- {check}" for check in failed_checks)


def _build_agent() -> Agent:
    """Create the specialized implementer agent used during task repair."""
    return Agent(
        role="Independent Implementer",
        goal=(
            "Fix failed implementation by addressing the root cause behind "
            "the checks that did not pass"
        ),
        backstory=(
            "You are an implementer focused on fixing the root cause of specific gaps. "
            "Read existing files, identify whether the problem is in imports, references, "
            "tests, exports, or implementation details, and fix the real source of failure. "
            f"{_TASK_REIMPLEMENTER_SUFFIX}"
        ),
        verbose=is_verbose(),
        allow_delegation=False,
        reasoning=False,
        llm=llm_complex,
        tools=[],
    )
