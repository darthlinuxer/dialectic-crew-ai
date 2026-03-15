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
import json
import re
from urllib.parse import unquote, urlparse
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from crewai.flow.flow import Flow, start, listen, router
from crewai.flow.persistence import SQLiteFlowPersistence, persist
from jsonschema import FormatChecker
from jsonschema.validators import validator_for
from pydantic import BaseModel, Field

from dialectic.app_logging import log_context
from dialectic.vision import VisionContext
from dialectic.hooks import HookScope
from dialectic.metrics import emit as emit_metric
from dialectic.flow_persistence import build_sqlite_flow_persistence
from execution.local_verification import (
    _check_adapter_sdk_contract_examples,
    _check_adapter_sdk_doc,
    _check_adapter_sdk_references,
    _check_adapter_conformance_cli,
    _check_capability_map_adr_reference,
    _check_capability_map_exists,
    _check_capability_map_gaps,
    _check_governance_doc,
    _check_governance_version_field,
    _check_governance_yaml,
    _check_high_impact_labeler_workflow,
    _check_high_impact_rules,
    _check_high_impact_telemetry,
    _check_sdk_ts_builds_types,
    _check_sdk_validate_manifest,
    _check_shim_deterministic_output,
    _check_shim_sample_manifests,
    _check_validator_shim_ci,
    _check_codeowners_governance_review,
    _check_generate_codeowners,
    _check_owners_registry,
    _check_validator_runner_gating,
    _check_validator_runner_outputs,
    _check_validator_runner_samples,
)
from execution.runtime import build_task_dialectic_crew
from execution.task_reimplement_runtime import build_task_flow_reimplementation_crew
from execution.task_verify_runtime import build_task_flow_verification_crew
from execution.validation_gate import run_stack_validation_gate
from schemas import (
    ValidationOutput,
    VerificationResult,
    TaskExecutionResult,
)

CREW_KICKOFF_TIMEOUT = int(os.getenv("CREW_KICKOFF_TIMEOUT", "300"))
DEFAULT_MIN_SCORE = float(os.getenv("MIN_QUALITY_SCORE", "7.5"))
DEFAULT_MAX_RETRIES = int(os.getenv("MAX_RETRIES_PER_TASK", "3"))
REVERIFY_AFTER_REIMPLEMENT_SCORE_THRESHOLD = float(
    os.getenv("REVERIFY_AFTER_REIMPLEMENT_SCORE_THRESHOLD", "9.0")
)
_MATERIALIZED_SECTION_STOP_RE = re.compile(
    r"^(?:Notes and guidance(?: for CI)?:|What I implemented|Next steps(?: / recommendations)?|If you want, I can:|Quick instructions(?: for running the validation)?|Retry checklist|Usage \(from repository root\):)\b",
    re.MULTILINE,
)
_MATERIALIZED_NEXT_SECTION_RE = re.compile(r"(?m)^\d+\)\s+[^\n]+$")
logger = logging.getLogger(__name__)


class TaskFlowState(BaseModel):
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
    current_phase: Literal["start", "dialectic", "verify", "reimplement", "completed", "failed"] = "start"


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

    def _run_independent_verifier(self, checks: list[str] | None = None) -> VerificationResult:
        checks_to_verify = checks or self.state.acceptance_checks
        crew = build_task_flow_verification_crew(
            task_id=self.state.task_id,
            task_title=self.state.task_title,
            task_description=self.state.task_description,
            acceptance_checks=checks_to_verify,
            vision_context=VisionContext(self.state.vision_context),
        )
        try:
            result = crew.kickoff()
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
        logger.debug("Dispatching task flow")
        return self.state.current_phase

    @router(dispatch)
    def route_from_dispatch(self):
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
                self.state.dialectic_notes = "Skipped dialectic: existing artifacts already satisfy acceptance checks."
                self.state.dialectic_success = True
                self.state.dialectic_retries = 0
                self.state.impl_output = "Existing repository artifacts already satisfy acceptance checks."
                self.state.verified = preverified.verified
                self.state.verification = preverified
                logger.info("Skipping task dialectic because existing artifacts already pass deterministic verification")
                print(f"   {self.state.task_id} dialectic skipped (existing artifacts already verified)")
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
                    result = crew.kickoff()

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
                    print(f"   {self.state.task_id} rejected (score {score}/10), retry {retry + 1}")
                    logger.warning("Task dialectic rejected")

            self.state.dialectic_score = score
            self.state.dialectic_notes = notes
            self.state.dialectic_success = False
            self.state.dialectic_retries = self.state.max_retries
            print(f"   {self.state.task_id} dialectic failed ({score}/10)")
            logger.error("Task dialectic failed")
            return "failed"

    @router(run_dialectic)
    def evaluate_dialectic(self):
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
                logger.info("Skipping verifier because deterministic verification already passed")
                print(f"   {self.state.task_id} verification: PASSED")
                return "done"

            if normalized == "owners.json exists and maps adapters to teams":
                return _check_owners_registry(repo_root)

            if normalized == "generate-codeowners.py produces CODEOWNERS file":
                return _check_generate_codeowners(repo_root)

            if normalized == "CODEOWNERS changes require governance approver review":
                return _check_codeowners_governance_review(repo_root)

            if normalized == "validator-runner produces signed report under prd_output/validator/":
                return _check_validator_runner_outputs(repo_root)

            if normalized == "sample PR demonstrates failing and passing cases with VisionContext.SELF ingestion logs":
                return _check_validator_runner_samples(repo_root)

            if normalized == "score >= 9.0 gating enforced when publish gating is enabled":
                return _check_validator_runner_gating(repo_root)

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
            print(f"   {self.state.task_id} starting independent re-implementation (Phase C)...")
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

            result = crew.kickoff()

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
                    if not self.state.phases_executed or self.state.phases_executed[-1] != "reverify":
                        self.state.phases_executed.append("reverify")
                    rerun = self._run_independent_verifier(failed_checks or self.state.acceptance_checks)
                    self.state.verification = rerun
                    self.state.verified = rerun.verified
                    self.state.reimplement_success = rerun.verified
                    status = "approved after re-verification" if rerun.verified else "failed re-verification"
                    print(
                        f"   {self.state.task_id} re-implementation {status} "
                        f"({validation.quality_score}/10)"
                    )
                else:
                    gate = run_stack_validation_gate("task")
                    self.state.verified = gate.verified
                    self.state.verification = VerificationResult(
                        verified=gate.verified,
                        checks_passed=(failed_checks or self.state.acceptance_checks) + gate.checks_passed,
                        checks_failed=gate.checks_failed,
                        notes=_join_verification_notes(
                            "High-confidence re-implementation accepted pending stack validation gate.",
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
                logger.error("Task reimplementation failed")
            return "done"

    @router(independent_reimplement)
    def evaluate_reimplement(self):
        if self.state.reimplement_success:
            self.state.current_phase = "completed"
            return "mark_completed"
        self.state.current_phase = "failed"
        return "mark_failed"

    # Router outputs remain string labels because CrewAI emits route names here,
    # not method references.
    @listen("mark_completed")
    def on_completed(self):
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
        with log_context(flow_id=self.flow_id, task_id=self.state.task_id, phase="failed"):
            self.state.current_phase = "failed"
            phases = " → ".join(self.state.phases_executed)
            logger.error("Task flow failed")
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
            verification=self.state.verification if self.state.verified or self.state.verification.notes else None,
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
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
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


def _run_local_verification_fallback(checks: list[str]) -> VerificationResult | None:
    """Evaluate common schema-style acceptance checks without the LLM verifier."""
    repo_root = Path.cwd().resolve()
    checks_passed: list[str] = []
    checks_failed: list[str] = []
    notes: list[str] = []
    handled = 0

    for check in checks:
        outcome = _evaluate_acceptance_check(check, repo_root)
        if outcome is None:
            continue
        handled += 1
        passed, note = outcome
        notes.append(note)
        if passed:
            checks_passed.append(check)
        else:
            checks_failed.append(check)

    if handled == 0:
        return None

    return VerificationResult(
        verified=not checks_failed,
        checks_passed=checks_passed,
        checks_failed=checks_failed,
        notes=_join_verification_notes("Local fallback verification executed.", *notes),
    )


def _evaluate_acceptance_check(check: str, repo_root: Path) -> tuple[bool, str] | None:
    normalized = check.strip()

    if normalized == "docs/dil/adapter_sdk.md committed":
        return _check_adapter_sdk_doc(repo_root)

    if normalized == "SDK spec references schema_checksum and determinism policy":
        return _check_adapter_sdk_references(repo_root)

    if normalized == "Examples for contract_schema_url verification included":
        return _check_adapter_sdk_contract_examples(repo_root)

    if normalized == "governance.yaml committed":
        return _check_governance_yaml(repo_root)

    if normalized == "docs/dil/governance.md authored explaining tie-breakers and anti-drift notes":
        return _check_governance_doc(repo_root)

    if normalized == "versioning field present in governance.yaml":
        return _check_governance_version_field(repo_root)

    if normalized == "sdk/ts/ builds TypeScript types from schemas":
        return _check_sdk_ts_builds_types(repo_root)

    if normalized == "validateManifest() exists and delegates to shim":
        return _check_sdk_validate_manifest(repo_root)

    if normalized == "dil-adapter-test CLI exists and produces artifacts/conformance/<adapterId>/report.json":
        return _check_adapter_conformance_cli(repo_root)

    if normalized == "crewai_capability_map.yaml exists with mappings for at least five capabilities":
        return _check_capability_map_exists(repo_root)

    if normalized == "ADR validation references crewai_capability_map.yaml":
        return _check_capability_map_adr_reference(repo_root)

    if normalized == "documented gaps for missing CrewAI-native alternatives":
        return _check_capability_map_gaps(repo_root)

    if normalized == "high_impact_rules.yaml exists with numeric thresholds":
        return _check_high_impact_rules(repo_root)

    if normalized == "high-impact-labeler workflow exists and labels PRs correctly":
        return _check_high_impact_labeler_workflow(repo_root)

    if normalized == "telemetry logs emitted to logs/governance/labels.jsonl for 30 days":
        return _check_high_impact_telemetry(repo_root)

    if normalized == "governance/determinism.md exists and documents fixture policy, seeds, and mirrors":
        return _check_determinism_policy_doc(repo_root)

    if normalized == "adapter_manifest.schema.json includes schema_checksum field":
        return _check_adapter_schema_checksum(repo_root)

    if normalized == "CI can reproduce deterministic output with pinned seed on at least two platforms":
        return _check_deterministic_ci_example(repo_root)

    if normalized == "validator-shim Docker image builds in CI":
        return _check_validator_shim_ci(repo_root)

    if normalized == "sample manifests pass validation via shim":
        return _check_shim_sample_manifests(repo_root)

    if normalized == "conformance JSON is produced deterministically by shim":
        return _check_shim_deterministic_output(repo_root)

    if normalized.endswith(" exists"):
        relative_path = normalized[: -len(" exists")].strip()
        target = repo_root / relative_path
        exists = target.exists()
        return exists, f"{relative_path}: {'present' if exists else 'missing'}"

    if "Schemas validate example manifests" in normalized:
        return _validate_schema_examples(repo_root)

    if "version_semver pattern enforcement" in normalized:
        return _check_version_semver_pattern(repo_root)

    if "contract_schema_url uses HTTPS" in normalized:
        return _check_https_contract_schema(repo_root)

    if "ISO-8601 deprecation_date validation" in normalized:
        return _check_deprecation_date_validation(repo_root)

    if "owner.sub-object includes required fields" in normalized:
        return _check_owner_required_fields(repo_root)

    return None


def _load_json_file(path: Path) -> Any:
    raw_text = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        payload = _extract_json_payload(raw_text)
        if payload is None:
            raise
        return json.loads(re.sub(r"(?ms)\s*/\*.*?\*/", "", payload))


def _load_schema_json(path: Path) -> tuple[dict | None, str | None]:
    try:
        loaded = _load_json_file(path)
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{path.relative_to(Path.cwd())}: {exc}"
    if not isinstance(loaded, dict):
        return None, f"{path.relative_to(Path.cwd())}: schema root must be a JSON object"
    return loaded, None


def _validate_schema_examples(repo_root: Path) -> tuple[bool, str]:
    adapter_schema_path = repo_root / "schemas/adapter_manifest.schema.json"
    registry_schema_path = repo_root / "schemas/registry_item.schema.json"

    adapter_schema, adapter_error = _load_schema_json(adapter_schema_path)
    if adapter_schema is None:
        return False, adapter_error or "adapter schema unreadable"

    registry_schema, registry_error = _load_schema_json(registry_schema_path)
    if registry_schema is None:
        return False, registry_error or "registry schema unreadable"

    adapter_validator = _build_jsonschema_validator(
        _inline_local_json_refs(adapter_schema, adapter_schema_path.parent)
    )
    registry_validator = _build_jsonschema_validator(
        _inline_local_json_refs(registry_schema, registry_schema_path.parent),
    )

    checks: list[tuple[Path, Any, bool]] = []
    checks.extend((path, adapter_validator, path.name.startswith("valid_")) for path in sorted((repo_root / "adapters/examples").glob("*.json")))
    checks.extend((path, registry_validator, path.name.startswith("valid_")) for path in sorted((repo_root / "registry/examples").glob("*.json")))
    if not checks:
        return False, "No example manifests found for schema validation fallback."

    failures: list[str] = []
    for path, validator, should_pass in checks:
        try:
            instance = _load_json_file(path)
            valid = validator.is_valid(instance)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"{path.relative_to(repo_root)} unreadable: {exc}")
            continue
        if should_pass and not valid:
            failures.append(f"{path.relative_to(repo_root)} should validate but did not")
        if not should_pass and valid:
            failures.append(f"{path.relative_to(repo_root)} should fail validation but passed")

    return (not failures), ("Schema/example validation passed." if not failures else "; ".join(failures))


def _build_jsonschema_validator(schema: dict) -> Any:
    validator_class = validator_for(schema)
    validator_class.check_schema(schema)
    return validator_class(schema, format_checker=FormatChecker())


def _inline_local_json_refs(
    value: Any,
    base_dir: Path,
    current_document: Any | None = None,
) -> Any:
    current_document = value if current_document is None else current_document

    if isinstance(value, dict):
        ref = value.get("$ref")
        if isinstance(ref, str):
            resolved = _resolve_local_json_ref(ref, base_dir, current_document)
            if resolved is not None:
                return _inline_local_json_refs(resolved, base_dir, resolved)
        return {
            key: _inline_local_json_refs(item, base_dir, current_document)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_inline_local_json_refs(item, base_dir, current_document) for item in value]
    return value


def _resolve_local_json_ref(ref: str, base_dir: Path, current_document: Any) -> Any | None:
    parsed = urlparse(ref)
    if parsed.scheme and parsed.scheme not in {"file"}:
        return None

    path_part = unquote(parsed.path)
    fragment = parsed.fragment

    if not path_part:
        if not fragment:
            return None
        return _resolve_json_pointer(current_document, fragment)

    if not path_part.endswith(".json"):
        return None

    target_path = (base_dir / path_part).resolve()
    target_schema, error = _load_schema_json(target_path)
    if target_schema is None:
        raise ValueError(error or f"Unreadable schema ref: {ref}")

    target_value: Any = target_schema
    if fragment:
        target_value = _resolve_json_pointer(target_schema, fragment)
    return _inline_local_json_refs(target_value, target_path.parent, target_schema)


def _resolve_json_pointer(document: Any, fragment: str) -> Any:
    pointer = fragment[1:] if fragment.startswith("/") else fragment
    current = document
    if not pointer:
        return current
    for raw_part in pointer.split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(part)]
        else:
            current = current[part]
    return current


def _check_version_semver_pattern(repo_root: Path) -> tuple[bool, str]:
    schema, error = _load_schema_json(repo_root / "schemas/adapter_manifest.schema.json")
    if schema is None:
        return False, error or "adapter schema unreadable"
    pattern = (
        schema.get("properties", {})
        .get("version_semver", {})
        .get("pattern")
    )
    passed = isinstance(pattern, str) and "\\." in pattern
    return passed, "version_semver pattern present." if passed else "version_semver pattern missing."


def _check_https_contract_schema(repo_root: Path) -> tuple[bool, str]:
    schema, error = _load_schema_json(repo_root / "schemas/adapter_manifest.schema.json")
    if schema is None:
        return False, error or "adapter schema unreadable"
    contract = schema.get("properties", {}).get("contract_schema_url", {})
    pattern = contract.get("pattern")
    passed = contract.get("format") == "uri" and isinstance(pattern, str) and pattern.startswith("^https://")
    return passed, "contract_schema_url enforces HTTPS URI." if passed else "contract_schema_url HTTPS enforcement missing."


def _check_deprecation_date_validation(repo_root: Path) -> tuple[bool, str]:
    schema, error = _load_schema_json(repo_root / "schemas/adapter_manifest.schema.json")
    if schema is None:
        return False, error or "adapter schema unreadable"
    deprecation = schema.get("properties", {}).get("deprecation_date", {})
    passed = deprecation.get("format") == "date-time"
    return passed, "deprecation_date uses ISO-8601 date-time validation." if passed else "deprecation_date format missing."


def _check_owner_required_fields(repo_root: Path) -> tuple[bool, str]:
    schema, error = _load_schema_json(repo_root / "schemas/adapter_manifest.schema.json")
    if schema is None:
        return False, error or "adapter schema unreadable"
    required = set(schema.get("properties", {}).get("owner", {}).get("required", []))
    expected = {"team_id", "primary_contact", "escalation_policy_url"}
    passed = expected.issubset(required)
    return passed, "owner required fields present." if passed else "owner required fields incomplete."


def _check_determinism_policy_doc(repo_root: Path) -> tuple[bool, str]:
    path = repo_root / "governance/determinism.md"
    if not path.exists():
        return False, "governance/determinism.md: missing"
    text = path.read_text(encoding="utf-8").lower()
    required_checks = {
        "60/30/10": bool(re.search(r"60\s*/\s*30\s*/\s*10", text)),
        "seed": "seed" in text,
        "mirror": "mirror" in text,
    }
    missing = [marker for marker, present in required_checks.items() if not present]
    if missing:
        return False, f"governance/determinism.md missing required topics: {', '.join(missing)}"
    return True, "governance/determinism.md documents fixture policy, seeds, and mirrors."


def _check_adapter_schema_checksum(repo_root: Path) -> tuple[bool, str]:
    candidate_paths = [
        repo_root / "schemas/adapter-manifest.schema.json",
        repo_root / "schemas/adapter_manifest.schema.json",
    ]
    for path in candidate_paths:
        if not path.exists():
            continue
        schema, error = _load_schema_json(path)
        if schema is None:
            return False, error or f"{path.relative_to(repo_root)} unreadable"
        schema_checksum = schema.get("properties", {}).get("schema_checksum")
        required = set(schema.get("required", []))
        if isinstance(schema_checksum, dict) and "schema_checksum" in required:
            return True, f"{path.relative_to(repo_root)} includes required schema_checksum field."
        return False, f"{path.relative_to(repo_root)} missing required schema_checksum field."
    return False, "No adapter manifest schema found for schema_checksum verification."


def _check_deterministic_ci_example(repo_root: Path) -> tuple[bool, str]:
    example_path = repo_root / "examples/canonicalization-run-seed-42.md"
    schema_path = repo_root / "examples/example-schema.json"
    tool_path = repo_root / "tools/canonicalize.py"

    missing_paths = [
        str(path.relative_to(repo_root))
        for path in (example_path, schema_path, tool_path)
        if not path.exists()
    ]
    if missing_paths:
        return False, f"Missing deterministic reproduction artifacts: {', '.join(missing_paths)}"

    text = example_path.read_text(encoding="utf-8").lower()
    required_markers = (
        "canonical_seed",
        "42",
        "sha256",
        "linux",
        "macos",
    )
    missing = [marker for marker in required_markers if marker not in text]
    if missing:
        return False, f"canonicalization example missing reproducibility markers: {', '.join(missing)}"
    return True, "Deterministic reproduction example documents pinned-seed verification across two platforms."


def _merge_verification_results(
    primary: VerificationResult,
    gate: VerificationResult,
) -> VerificationResult:
    return VerificationResult(
        verified=primary.verified and gate.verified,
        checks_passed=_dedupe_preserve_order(primary.checks_passed + gate.checks_passed),
        checks_failed=_dedupe_preserve_order(primary.checks_failed + gate.checks_failed),
        notes=_join_verification_notes(primary.notes, gate.notes),
    )


def _join_verification_notes(*parts: str) -> str:
    return " | ".join(part for part in parts if part)


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered
