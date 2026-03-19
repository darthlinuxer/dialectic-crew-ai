"""Deterministic remediation helpers for self-improve quality-gate failures."""

# pylint: disable=import-outside-toplevel,too-many-locals

from __future__ import annotations

from importlib import import_module
import logging
from pathlib import Path

from .quality_gate_helpers import DEFAULT_QUALITY_GATE_TIMEOUT
from .quality_gate_models import QualityCheckResult, RemediationAction


logger = logging.getLogger(__name__)


def _quality_gate_module():
    return import_module("src.main.self_improve.quality_gate")


def python_remediation_actions(
    project_root: Path,
    touched_files: list[str],
) -> list[RemediationAction]:
    """Return bounded Python remediation actions for touched files."""
    quality_gate = _quality_gate_module()
    if not touched_files or not quality_gate.command_available("ruff"):
        return []

    targets = quality_gate.resolve_python_targets(
        project_root,
        "src/",
        touched_files=touched_files,
    )
    if not targets:
        return []

    return [
        RemediationAction(
            label="ruff-format-fix",
            command=["ruff", "format", *targets],
            reason="Apply deterministic Ruff formatting to touched Python files.",
        ),
        RemediationAction(
            label="ruff-lint-fix",
            command=["ruff", "check", "--fix", *targets],
            reason="Apply deterministic Ruff lint fixes to touched Python files.",
        ),
    ]


def run_python_remediation(
    project_root: Path,
    touched_files: list[str],
) -> tuple[bool, list[str]]:
    """Run bounded Python remediation and report whether any change was attempted."""
    quality_gate = _quality_gate_module()
    executed_steps: list[str] = []
    for action in python_remediation_actions(project_root, touched_files):
        logger.info("Running remediation step %s: %s", action.label, action.reason)
        quality_gate.run_cmd(
            action.command,
            project_root,
            timeout=DEFAULT_QUALITY_GATE_TIMEOUT,
        )
        executed_steps.append(action.label)
    return bool(executed_steps), executed_steps


def should_attempt_python_remediation(
    checks: list[QualityCheckResult],
    touched_files: list[str],
) -> bool:
    """Return whether failed checks warrant deterministic Python remediation."""
    if not touched_files:
        return False
    failing_tools = {check.tool for check in checks if not check.passed}
    return bool(failing_tools & {"ruff", "ruff-format"})


def should_attempt_crew_remediation(
    checks: list[QualityCheckResult],
    touched_files: list[str],
) -> bool:
    """Return whether failed checks warrant the opt-in quality repair crew."""
    if not touched_files:
        return False
    failing_tools = {check.tool for check in checks if not check.passed}
    return bool(failing_tools & {"mypy", "pyright"})


def _render_failed_checks(checks: list[QualityCheckResult]) -> str:
    lines: list[str] = []
    for check in checks:
        if check.passed:
            continue
        lines.append(f"- {check.tool}: {check.output[:500] or 'failed'}")
        for error in check.errors[:5]:
            lines.append(f"  - {error}")
    return "\n".join(lines) or "- No structured failure details were captured."


def _build_quality_remediation_crew(
    *,
    touched_files: list[str],
    checks: list[QualityCheckResult],
):
    from crewai import Agent, Crew, Task

    from dialectic.agents import create_validador_macro
    from dialectic.crew_builder import build_sequential_crew
    from dialectic.crew_verbose_config import is_verbose
    from dialectic.crewai_runtime import run_crew_kickoff
    from dialectic.knowledge import style_guide_knowledge, vision_knowledge
    from dialectic.llm import llm_complex
    from dialectic.vision import VisionContext, normalize_vision_context
    from schemas import ValidationOutput

    del run_crew_kickoff
    vision_context = normalize_vision_context(VisionContext.SELF)
    touched_block = "\n".join(f"- {path}" for path in touched_files)
    repair_agent = Agent(
        role="Quality Repair Implementer",
        goal=(
            "Fix the root cause behind static-analysis failures using the smallest "
            "safe code change set"
        ),
        backstory=(
            "You repair Python code after automated validation failed. Work from the "
            "reported errors, prefer minimal safe edits, and return plain text only. "
            "Do not call tools. When code must change, emit complete file sections in "
            "the exact format `--- relative/path/to/file.ext ---` followed by the "
            "complete final file contents. If no safe change is needed, return exactly "
            "NO_FILE_CHANGES. Prefer touching only the listed touched files unless a "
            "directly related import or shared type must also change."
        ),
        verbose=is_verbose(),
        allow_delegation=False,
        reasoning=False,
        llm=llm_complex,
        tools=[],
    )
    validator = create_validador_macro(vision_context)

    repair_task = Task(
        description=(
            "Self-improve quality validation failed for Python static analysis.\n\n"
            f"TOUCHED FILES:\n{touched_block}\n\n"
            f"FAILED CHECKS:\n{_render_failed_checks(checks)}\n\n"
            "Diagnose the root cause before changing code. Focus on mypy and pyright "
            "failures first. Avoid broad refactors. Return a short summary plus full "
            "file sections for every changed file, or exactly NO_FILE_CHANGES if you "
            "cannot produce a safe bounded repair."
        ),
        expected_output=(
            "Plain-text root-cause summary plus complete file sections when files "
            "must change"
        ),
        agent=repair_agent,
    )
    validation_task = Task(
        description=(
            "Evaluate whether the proposed remediation is a safe, minimal fix for the "
            "reported mypy/pyright failures. Approve only if the patch is focused, "
            "likely to resolve the reported root cause, and unlikely to create drift."
        ),
        expected_output="ValidationOutput",
        output_pydantic=ValidationOutput,
        agent=validator,
        context=[repair_task],
    )

    knowledge_sources = [vision_knowledge(vision_context)]
    if vision_context.value == VisionContext.SELF.value:
        knowledge_sources.extend(style_guide_knowledge())

    return build_sequential_crew(
        crew_factory=Crew,
        agents=[repair_agent, validator],
        tasks=[repair_task, validation_task],
        knowledge_sources=knowledge_sources,
        memory=None,
    )


def run_crew_remediation(
    project_root: Path,
    touched_files: list[str],
    checks: list[QualityCheckResult],
) -> tuple[bool, list[str], str]:
    """Run the opt-in repair crew and materialize any bounded file-section output."""
    from dialectic.crewai_runtime import run_crew_kickoff
    from execution.task_flow import _materialize_generated_files
    from schemas import ValidationOutput

    if not should_attempt_crew_remediation(checks, touched_files):
        return False, [], ""

    crew = _build_quality_remediation_crew(
        touched_files=touched_files,
        checks=checks,
    )
    result = run_crew_kickoff(crew)
    tasks_out = getattr(result, "tasks_output", None) or []
    impl_raw = getattr(tasks_out[0], "raw", "") if tasks_out else ""
    validation = None
    if tasks_out:
        last_pydantic = getattr(tasks_out[-1], "pydantic", None)
        if isinstance(last_pydantic, ValidationOutput):
            validation = last_pydantic

    summary = (
        validation.final_validation_notes
        if validation and validation.final_validation_notes
        else "Quality repair crew executed."
    )
    if validation is not None and not validation.consensus_reached:
        return False, [], summary

    if impl_raw.strip() == "NO_FILE_CHANGES":
        return False, [], summary

    materialized = _materialize_generated_files(impl_raw, repo_root=project_root)
    if not materialized:
        return False, [], summary

    materialized_steps = [
        f"write:{Path(path).resolve().relative_to(project_root.resolve())}"
        for path in materialized
    ]
    return True, ["quality-repair-crew", *materialized_steps], summary
