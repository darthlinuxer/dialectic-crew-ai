"""
Per-task execution Flow with verification and conditional re-implementation.

Uses native CrewAI Flow features:
- @router() for conditional branching: if verify (A) fails → reimplement (C)
- @start/@listen for event-driven execution phases
- reasoning=True for the independent verification agent

Flow structure:
  @start() run_dialectic → @router evaluate_dialectic
    ├── "verify"  → verify_implementation → @router evaluate_verification
    │                ├── "completed" → on_completed
    │                └── "reimplement" → independent_reimplement → @router evaluate_reimplement
    │                                     ├── "completed" → on_completed
    │                                     └── "failed" → on_failed
    └── "failed"  → on_failed
"""

import os
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import uuid4

from crewai.flow.flow import Flow, start, listen, router
from crewai.flow.persistence import SQLiteFlowPersistence, persist
from pydantic import BaseModel, Field

from dialectic.app_logging import log_context
from dialectic.crewai_runtime import run_crew_kickoff
from dialectic.flow_persistence import build_sqlite_flow_persistence
from dialectic.hooks import HookScope
from dialectic.metrics import emit as emit_metric
from dialectic.vision import VisionContext
from schemas import (
    ValidationOutput,
    VerificationResult,
    TaskExecutionResult,
)
from .local_verification import (
    _join_verification_notes,
    _merge_verification_results,
    _run_local_verification_fallback,
)
from .runtime import build_task_dialectic_crew
from .task_reimplement_runtime import build_task_flow_reimplementation_crew
from .task_verify_runtime import build_task_flow_verification_crew
from .validation_gate import run_stack_validation_gate

CREW_KICKOFF_TIMEOUT = int(os.getenv("CREW_KICKOFF_TIMEOUT", "300"))
DEFAULT_MIN_SCORE = float(os.getenv("MIN_QUALITY_SCORE", "7.5"))
DEFAULT_MAX_RETRIES = int(os.getenv("MAX_RETRIES_PER_TASK", "3"))
REVERIFY_AFTER_REIMPLEMENT_SCORE_THRESHOLD = float(
    os.getenv("REVERIFY_AFTER_REIMPLEMENT_SCORE_THRESHOLD", "9.0")
)
_MATERIALIZED_SECTION_STOP_RE = re.compile(
    (
        r"^(?:Notes and guidance(?: for CI)?:|What I implemented|"
        r"Next steps(?: / recommendations)?|If you want, I can:|"
        r"Quick instructions(?: for running the validation)?|"
        r"Retry checklist|Usage \(from repository root\):)\b"
    ),
    re.MULTILINE,
)
_MATERIALIZED_NEXT_SECTION_RE = re.compile(r"(?m)^\d+\)\s+[^\n]+$")
logger = logging.getLogger(__name__)


class TaskFlowState(BaseModel):
    """Persistent state for per-task dialectic execution and verification."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    task_title: str = ""
    task_description: str = ""
    context_str: str = ""
    output_dir: str = ""
    acceptance_checks: list[str] = Field(default_factory=list)
    min_score: float = DEFAULT_MIN_SCORE
    max_retries: int = DEFAULT_MAX_RETRIES
    vision_context: str = VisionContext.PROJECT.value

    # Dialectic results
    dialectic_score: float = 0.0
    dialectic_notes: str = ""
    dialectic_success: bool = False
    dialectic_retries: int = 0
    impl_output: str = ""

    # Verification results (Phase A+B)
    verified: bool = False
    verification: VerificationResult = Field(default_factory=VerificationResult)

    # Reimplement results (Phase C)
    reimplement_score: float = 0.0
    reimplement_success: bool = False
    reimplement_output: str = ""

    # Final result
    phases_executed: list[str] = Field(default_factory=list)
    current_phase: Literal[
        "start",
        "dialectic",
        "verify",
        "reimplement",
        "completed",
        "failed",
    ] = "start"


@lru_cache(maxsize=1)
def _get_task_persistence() -> SQLiteFlowPersistence:
    return build_sqlite_flow_persistence()


@persist()
class TaskExecutionFlow(Flow[TaskFlowState]):
    """
    Per-task execution with three phases and state persistence:
    1. Dialectic cycle (implement → critique → synthesize → validate)
    2. Post-execution verification (A) with acceptance criteria (B)
    3. Independent re-implementation (C) if verification fails
    """

    def _run_independent_verifier(
        self,
        checks: list[str] | None = None,
    ) -> VerificationResult:
        """Run the independent verifier and merge stack-gate results when it passes."""
        checks_to_verify = checks or self.state.acceptance_checks
        crew = build_task_flow_verification_crew(
            task_id=self.state.task_id,
            task_title=self.state.task_title,
            task_description=self.state.task_description,
            acceptance_checks=checks_to_verify,
            vision_context=VisionContext(self.state.vision_context),
        )
        try:
            result = run_crew_kickoff(crew)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Independent verifier raised an exception: %s", exc)
            fallback = _run_local_verification_fallback(checks_to_verify)
            if fallback is not None:
                logger.info("Recovered verifier failure with local acceptance fallback")
                return fallback
            return VerificationResult(
                verified=False,
                checks_failed=list(checks_to_verify or []),
                notes=f"Verifier execution failed: {exc}",
            )

        pydantic_result = getattr(result, "pydantic", None)
        verification: VerificationResult | None = None
        if isinstance(pydantic_result, VerificationResult):
            verification = pydantic_result

        tasks_out = getattr(result, "tasks_output", None) or []
        if verification is None and tasks_out:
            last_p = getattr(tasks_out[-1], "pydantic", None)
            if isinstance(last_p, VerificationResult):
                verification = last_p

        if verification is None:
            fallback = _run_local_verification_fallback(checks_to_verify)
            if fallback is not None:
                logger.info("Recovered missing VerificationResult with local acceptance fallback")
                return fallback
            return VerificationResult(
                verified=False,
                notes="Failed to obtain structured VerificationResult",
            )

        if not verification.verified:
            return verification

        gate = run_stack_validation_gate("task")
        return _merge_verification_results(verification, gate)

    @start()
    def dispatch(self):
        """Emit the current phase so the flow can resume from persisted state."""
        logger.debug("Dispatching task flow")
        return self.state.current_phase

    @router(dispatch)
    def route_from_dispatch(self):
        """Route persisted state to the next flow stage."""
        phase = self.state.current_phase
        if phase == "verify":
            return "verify"
        if phase == "reimplement":
            return "reimplement"
        if phase == "completed":
            return "mark_completed"
        if phase == "failed":
            return "mark_failed"

        self.state.current_phase = "dialectic"
        return "start_dialectic"

    @listen("start_dialectic")
    # pylint: disable=too-many-locals,too-many-statements
    def run_dialectic(self):
        """Phase 0: Full dialectic cycle with retries."""
        with log_context(
            flow_id=self.flow_id,
            task_id=self.state.task_id,
            phase="dialectic",
            vision_context=self.state.vision_context,
        ):
            self.state.current_phase = "dialectic"
            if not self.state.phases_executed or self.state.phases_executed[-1] != "dialectic":
                self.state.phases_executed.append("dialectic")
            synthesis_for_retry: str | None = None
            vision_context = VisionContext(self.state.vision_context)
            score = 0.0
            notes = "No structured output"

            preverified = _run_local_verification_fallback(self.state.acceptance_checks)
            if preverified is not None and preverified.verified:
                self.state.dialectic_score = self.state.min_score
                self.state.dialectic_notes = (
                    "Skipped dialectic: existing artifacts already satisfy "
                    "acceptance checks."
                )
                self.state.dialectic_success = True
                self.state.dialectic_retries = 0
                self.state.impl_output = (
                    "Existing repository artifacts already satisfy acceptance checks."
                )
                self.state.verified = preverified.verified
                self.state.verification = preverified
                logger.info(
                    "Skipping task dialectic because existing artifacts already "
                    "pass deterministic verification"
                )
                print(
                    f"   {self.state.task_id} dialectic skipped "
                    "(existing artifacts already verified)"
                )
                return "passed"

            for retry in range(self.state.max_retries + 1):
                logger.info("Task dialectic iteration", extra={"retry": retry})
                crew = build_task_dialectic_crew(
                    task_id=self.state.task_id,
                    task_title=self.state.task_title,
                    task_description=self.state.task_description,
                    context_str=self.state.context_str,
                    min_score=self.state.min_score,
                    vision_context=vision_context,
                    synthesis_for_retry=synthesis_for_retry,
                    retry=retry,
                    max_retries=self.state.max_retries,
                )

                with HookScope(
                    token_budget=0,
                    allowed_write_roots=(
                        frozenset({str(Path(self.state.output_dir).resolve())})
                        if self.state.output_dir
                        else None
                    ),
                    label=f"task/{self.state.task_id}",
                ):
                    result = run_crew_kickoff(crew)

                validation: ValidationOutput | None = None
                tasks_out = getattr(result, "tasks_output", None) or []
                if tasks_out:
                    last_p = getattr(tasks_out[-1], "pydantic", None)
                    if isinstance(last_p, ValidationOutput):
                        validation = last_p

                score = validation.quality_score if validation else 5.0
                notes = validation.final_validation_notes if validation else "No structured output"

                impl_raw = ""
                synthesis_raw = ""
                if tasks_out and len(tasks_out) >= 1:
                    impl_raw = getattr(tasks_out[0], "raw", "") or ""
                if tasks_out and len(tasks_out) >= 3:
                    synthesis_raw = getattr(tasks_out[2], "raw", "") or ""
                best_raw = synthesis_raw or impl_raw

                if score >= self.state.min_score:
                    self.state.dialectic_score = score
                    self.state.dialectic_notes = notes
                    self.state.dialectic_success = True
                    self.state.dialectic_retries = retry
                    self.state.impl_output = best_raw
                    materialized = _materialize_generated_files(best_raw)
                    if materialized:
                        logger.info(
                            "Materialized implementation artifacts from dialectic output",
                            extra={"count": len(materialized), "task_id": self.state.task_id},
                        )
                    print(f"   {self.state.task_id} dialectic approved (score {score}/10)")
                    logger.info("Task dialectic approved")
                    return "passed"

                if tasks_out and len(tasks_out) >= 3:
                    synthesis_for_retry = getattr(tasks_out[2], "raw", "") or ""
                else:
                    synthesis_for_retry = notes

                if retry < self.state.max_retries:
                    print(
                        f"   {self.state.task_id} rejected "
                        f"(score {score}/10), retry {retry + 1}"
                    )
                    logger.warning("Task dialectic rejected")

            self.state.dialectic_score = score
            self.state.dialectic_notes = notes
            self.state.dialectic_success = False
            self.state.dialectic_retries = self.state.max_retries
            print(f"   {self.state.task_id} dialectic failed ({score}/10)")
            logger.error(
                "Task dialectic failed: task_id=%s score=%.1f/%s notes=%s",
                self.state.task_id,
                score,
                10,
                notes[:240],
                extra={
                    "event_type": "task_flow_failure",
                    "event_name": "task_dialectic_failed",
                    "task_id": self.state.task_id,
                    "dialectic_score": score,
                    "dialectic_notes": notes[:240],
                },
            )
            return "failed"

    @router(run_dialectic)
    def evaluate_dialectic(self):
        """Advance to verification when dialectic succeeds, otherwise fail the flow."""
        if self.state.dialectic_success:
            self.state.current_phase = "verify"
            return "verify"
        self.state.current_phase = "failed"
        return "mark_failed"

    # Router outputs remain string labels because CrewAI emits route names here,
    # not method references.
    @listen("verify")
    def verify_implementation(self):
        """Phase A: Verify artifacts + Phase B: Check acceptance criteria."""
        with log_context(flow_id=self.flow_id, task_id=self.state.task_id, phase="verify"):
            self.state.current_phase = "verify"
            if not self.state.phases_executed or self.state.phases_executed[-1] != "verify":
                self.state.phases_executed.append("verify")

            if self.state.verified and self.state.verification.verified:
                logger.info(
                    "Skipping verifier because deterministic verification already "
                    "passed"
                )
                print(f"   {self.state.task_id} verification: PASSED")
                return "done"

            vr = self._run_independent_verifier()
            self.state.verified = vr.verified
            self.state.verification = vr

            status = "PASSED" if self.state.verified else "FAILED"
            logger.info("Task verification finished")
            print(f"   {self.state.task_id} verification: {status}")
            if self.state.verification.checks_failed:
                print(f"      Failed checks: {self.state.verification.checks_failed}")
            return "done"

    @router(verify_implementation)
    def evaluate_verification(self):
        """Choose completion or reimplementation based on verifier output."""
        if self.state.verified:
            self.state.current_phase = "completed"
            return "mark_completed"
        self.state.current_phase = "reimplement"
        return "reimplement"

    # Router outputs remain string labels because CrewAI emits route names here,
    # not method references.
    @listen("reimplement")
    def independent_reimplement(self):
        """Phase C: Focused re-implementation using failed checks plus condensed context."""
        with log_context(flow_id=self.flow_id, task_id=self.state.task_id, phase="reimplement"):
            self.state.current_phase = "reimplement"
            if not self.state.phases_executed or self.state.phases_executed[-1] != "reimplement":
                self.state.phases_executed.append("reimplement")
            print(
                f"   {self.state.task_id} starting independent "
                "re-implementation (Phase C)..."
            )
            logger.info("Starting task reimplementation")
            vision_context = VisionContext(self.state.vision_context)

            failed_checks = self.state.verification.checks_failed
            crew = build_task_flow_reimplementation_crew(
                task_id=self.state.task_id,
                task_title=self.state.task_title,
                task_description=self.state.task_description,
                failed_checks=failed_checks,
                verification_notes=self.state.verification.notes,
                dialectic_context=_build_dialectic_context(
                    self.state.dialectic_notes,
                    self.state.impl_output,
                ),
                min_score=self.state.min_score,
                vision_context=vision_context,
            )

            result = run_crew_kickoff(crew)

            validation: ValidationOutput | None = None
            tasks_out = getattr(result, "tasks_output", None) or []
            if tasks_out:
                last_p = getattr(tasks_out[-1], "pydantic", None)
                if isinstance(last_p, ValidationOutput):
                    validation = last_p

            if validation and validation.quality_score >= self.state.min_score:
                self.state.reimplement_score = validation.quality_score
                impl_raw = getattr(tasks_out[0], "raw", "") if tasks_out else ""
                self.state.reimplement_output = impl_raw
                materialized = _materialize_generated_files(impl_raw)
                if materialized:
                    logger.info(
                        "Materialized implementation artifacts from reimplementation output",
                        extra={"count": len(materialized), "task_id": self.state.task_id},
                    )
                if validation.quality_score < REVERIFY_AFTER_REIMPLEMENT_SCORE_THRESHOLD:
                    if (
                        not self.state.phases_executed
                        or self.state.phases_executed[-1] != "reverify"
                    ):
                        self.state.phases_executed.append("reverify")
                    rerun = self._run_independent_verifier(
                        failed_checks or self.state.acceptance_checks
                    )
                    self.state.verification = rerun
                    self.state.verified = rerun.verified
                    self.state.reimplement_success = rerun.verified
                    status = (
                        "approved after re-verification"
                        if rerun.verified
                        else "failed re-verification"
                    )
                    print(
                        f"   {self.state.task_id} re-implementation {status} "
                        f"({validation.quality_score}/10)"
                    )
                else:
                    gate = run_stack_validation_gate("task")
                    self.state.verified = gate.verified
                    self.state.verification = VerificationResult(
                        verified=gate.verified,
                        checks_passed=(
                            failed_checks or self.state.acceptance_checks
                        )
                        + gate.checks_passed,
                        checks_failed=gate.checks_failed,
                        notes=_join_verification_notes(
                            (
                                "High-confidence re-implementation accepted "
                                "pending stack validation gate."
                            ),
                            gate.notes,
                        ),
                    )
                    self.state.reimplement_success = gate.verified
                    status = "approved" if gate.verified else "failed stack validation"
                    print(
                        f"   {self.state.task_id} re-implementation {status} "
                        f"({validation.quality_score}/10)"
                    )
                logger.info("Task reimplementation finished")
            else:
                score = validation.quality_score if validation else 0.0
                self.state.reimplement_score = score
                self.state.reimplement_success = False
                print(f"   {self.state.task_id} re-implementation failed ({score}/10)")
                logger.error(
                    "Task reimplementation failed: task_id=%s score=%.1f/%s checks_failed=%s",
                    self.state.task_id,
                    score,
                    10,
                    self.state.verification.checks_failed,
                    extra={
                        "event_type": "task_flow_failure",
                        "event_name": "task_reimplementation_failed",
                        "task_id": self.state.task_id,
                        "reimplement_score": score,
                        "checks_failed": list(self.state.verification.checks_failed),
                    },
                )
            return "done"

    @router(independent_reimplement)
    def evaluate_reimplement(self):
        """Finish the flow after reimplementation succeeds or fails."""
        if self.state.reimplement_success:
            self.state.current_phase = "completed"
            return "mark_completed"
        self.state.current_phase = "failed"
        return "mark_failed"

    # Router outputs remain string labels because CrewAI emits route names here,
    # not method references.
    @listen("mark_completed")
    def on_completed(self):
        """Emit metrics and return the final success payload."""
        with log_context(flow_id=self.flow_id, task_id=self.state.task_id, phase="completed"):
            self.state.current_phase = "completed"
            phases = " → ".join(self.state.phases_executed)
            logger.info("Task flow completed")
            print(f"   {self.state.task_id} COMPLETED (phases: {phases})")
            emit_metric(
                "task_score",
                max(self.state.dialectic_score, self.state.reimplement_score),
                task_id=self.state.task_id,
                success=True,
                vision_context=self.state.vision_context,
            )
            emit_metric(
                "task_retry_count",
                float(self.state.dialectic_retries),
                task_id=self.state.task_id,
                vision_context=self.state.vision_context,
            )
            return self._build_result(success=True)

    # Router outputs remain string labels because CrewAI emits route names here,
    # not method references.
    @listen("mark_failed")
    def on_failed(self):
        """Emit metrics and return the final failure payload."""
        with log_context(flow_id=self.flow_id, task_id=self.state.task_id, phase="failed"):
            self.state.current_phase = "failed"
            phases = " → ".join(self.state.phases_executed)
            logger.error(
                (
                    "Task flow failed: task_id=%s phases=%s dialectic_score=%.1f "
                    "reimplement_score=%.1f checks_failed=%s"
                ),
                self.state.task_id,
                phases,
                self.state.dialectic_score,
                self.state.reimplement_score,
                self.state.verification.checks_failed,
                extra={
                    "event_type": "task_flow_failure",
                    "event_name": "task_flow_failed",
                    "task_id": self.state.task_id,
                    "execution_phases": list(self.state.phases_executed),
                    "dialectic_score": self.state.dialectic_score,
                    "reimplement_score": self.state.reimplement_score,
                    "checks_failed": list(self.state.verification.checks_failed),
                },
            )
            print(f"   {self.state.task_id} FAILED (phases: {phases})")
            emit_metric(
                "task_score",
                max(self.state.dialectic_score, self.state.reimplement_score),
                task_id=self.state.task_id,
                success=False,
                vision_context=self.state.vision_context,
            )
            emit_metric(
                "task_retry_count",
                float(self.state.dialectic_retries),
                task_id=self.state.task_id,
                vision_context=self.state.vision_context,
            )
            return self._build_result(success=False)

    def _build_result(self, success: bool) -> TaskExecutionResult:
        """Construct the final task execution result from accumulated state."""
        best_score = max(
            self.state.dialectic_score,
            self.state.reimplement_score,
        )
        best_output = self.state.reimplement_output or self.state.impl_output
        notes = self.state.dialectic_notes
        if self.state.verification.notes:
            notes += f" | Verification: {self.state.verification.notes[:300]}"

        return TaskExecutionResult(
            task_id=self.state.task_id,
            title=self.state.task_title,
            success=success,
            score=best_score,
            retry_count=self.state.dialectic_retries,
            output_paths=[self.state.output_dir] if self.state.output_dir else [],
            validation_notes=notes[:1000],
            output_summary=best_output[:5000],
            verification=(
                self.state.verification
                if self.state.verified or self.state.verification.notes
                else None
            ),
            execution_phases=self.state.phases_executed,
        )


def _build_dialectic_context(dialectic_notes: str, impl_output: str) -> str:
    """Condense the prior dialectic reasoning for reimplementation context."""
    notes = (dialectic_notes or "").strip()
    implementation_excerpt = (impl_output or "").strip()[:1500]
    parts: list[str] = []
    if notes:
        parts.append("DIALECTIC NOTES:\n" + notes[:1200])
    if implementation_excerpt:
        parts.append("IMPLEMENTATION EXCERPT:\n" + implementation_excerpt)
    return "\n\n".join(parts)


def _materialize_generated_files(raw_output: str, repo_root: Path | None = None) -> list[str]:
    """Write numbered file-content sections from model output into the repository.

    This is a narrow fallback for execution stages that returned detailed file payloads
    in plain text but failed to complete the final tool-writing step.
    """
    base_dir = (repo_root or Path.cwd()).resolve()
    written_paths: list[str] = []
    for relative_path, content in _extract_generated_files(raw_output):
        target_path = _resolve_materialization_path(base_dir, relative_path)
        if target_path is None:
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(
            _sanitize_materialized_content(relative_path, content),
            encoding="utf-8",
        )
        written_paths.append(str(target_path))
    return written_paths


def _extract_generated_files(raw_output: str) -> list[tuple[str, str]]:
    """Parse common file-content section formats from model output."""
    text = (raw_output or "").strip()
    if not text:
        return []

    extracted: list[tuple[str, str]] = []
    seen_paths: set[str] = set()

    for relative_path, content in _extract_dashed_file_sections(text):
        if relative_path in seen_paths:
            continue
        seen_paths.add(relative_path)
        extracted.append((relative_path, content))

    for relative_path, content in _extract_numbered_file_sections(text):
        if relative_path in seen_paths:
            continue
        seen_paths.add(relative_path)
        extracted.append((relative_path, content))

    return extracted


def _extract_numbered_file_sections(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^(\d+)\)\s+([^\n]+)\n", text))
    if not matches:
        return []

    extracted: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        relative_path = _normalize_materialized_relative_path(match.group(2))
        if not _looks_like_relative_file_path(relative_path):
            continue
        section_start = match.end()
        section_end = (
            matches[index + 1].start() if index + 1 < len(matches) else len(text)
        )
        content = _trim_materialized_section(text[section_start:section_end])
        if content:
            extracted.append((relative_path, content))
    return extracted


def _extract_dashed_file_sections(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"(?m)^---\s+([^\n]+?)\s+---\n", text))
    if not matches:
        return []

    extracted: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        relative_path = _normalize_materialized_relative_path(match.group(1))
        if not _looks_like_relative_file_path(relative_path):
            continue
        section_start = match.end()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        content = _trim_materialized_section(text[section_start:section_end])
        if content:
            extracted.append((relative_path, content))
    return extracted


def _trim_materialized_section(content: str) -> str:
    stop_match = _MATERIALIZED_SECTION_STOP_RE.search(content)
    if stop_match:
        content = content[: stop_match.start()]
    next_section_match = _MATERIALIZED_NEXT_SECTION_RE.search(content)
    if next_section_match:
        content = content[: next_section_match.start()]
    return content.strip()


def _normalize_materialized_relative_path(relative_path: str) -> str:
    candidate = relative_path.strip().strip("`")
    while True:
        trimmed = re.sub(r"\s+\([^()\n]*\)$", "", candidate).strip()
        if trimmed == candidate or not _looks_like_relative_file_path(trimmed):
            return candidate
        candidate = trimmed


def _looks_like_relative_file_path(relative_path: str) -> bool:
    candidate = Path(relative_path.strip())
    return not candidate.is_absolute() and (len(candidate.parts) > 1 or bool(candidate.suffix))


def _resolve_materialization_path(base_dir: Path, relative_path: str) -> Path | None:
    candidate = Path(relative_path.strip())
    if candidate.is_absolute():
        return None
    resolved = (base_dir / candidate).resolve()
    try:
        resolved.relative_to(base_dir)
    except ValueError:
        logger.warning("Skipping unsafe materialization path: %s", relative_path)
        return None
    return resolved


def _sanitize_materialized_content(relative_path: str, content: str) -> str:
    sanitized = content.strip()
    if relative_path.endswith(".json"):
        sanitized = _extract_json_payload(sanitized) or sanitized
        sanitized = re.sub(r"(?ms)\s*/\*.*?\*/", "", sanitized)
    return sanitized.rstrip() + "\n"


def _extract_json_payload(content: str) -> str | None:
    payload_start = next((index for index, char in enumerate(content) if char in "[{"), -1)
    if payload_start < 0:
        return None

    opener = content[payload_start]
    closer = "]" if opener == "[" else "}"
    depth = 0
    in_string = False
    escape = False

    for index in range(payload_start, len(content)):
        char = content[index]
        if in_string:
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
            continue
        if char == opener:
            depth += 1
            continue
        if char == closer:
            depth -= 1
            if depth == 0:
                return content[payload_start : index + 1]

    return None
