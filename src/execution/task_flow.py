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

import json
import os
from typing import Any, Literal
from uuid import uuid4

from crewai import Task, Crew, Agent, Process
from crewai.flow.flow import Flow, start, listen, router
from crewai.flow.persistence import SQLiteFlowPersistence, persist
from pydantic import BaseModel, Field

from dialectic.agents import (
    _vision_label,
    crew_memory,
    create_implementer,
    create_validador_macro,
    create_critico_socratico,
    create_sintetizador,
    llm_planning,
    llm_complex,
    llm_simple,
    vision_knowledge,
)
from dialectic.vision import VisionContext
from dialectic.tools import file_read_tool, file_write_tool, directory_read_tool
from dialectic.hooks import HookScope
from dialectic.metrics import emit as emit_metric
from dialectic.flow_persistence import build_sqlite_flow_persistence
from execution.runtime import build_task_dialectic_crew
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


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------


def _guardrail_success_output(result, validated_model: BaseModel) -> str:
    """Return a CrewAI-compatible guardrail payload for structured outputs."""
    return validated_model.model_dump_json()

def _quality_guardrail(result) -> tuple[bool, Any]:
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, ValidationOutput):
        if 0.0 <= pydantic_obj.quality_score <= 10.0:
            return (True, _guardrail_success_output(result, pydantic_obj))
        emit_metric("guardrail_reject", 1.0, guardrail="quality", reason="score_out_of_range")
        return (False, "quality_score must be between 0.0 and 10.0")
    emit_metric("guardrail_reject", 1.0, guardrail="quality", reason="invalid_schema")
    return (False, "Output must be valid JSON: quality_score, consensus_reached, final_validation_notes")


def _verification_guardrail(result) -> tuple[bool, Any]:
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, VerificationResult):
        return (True, _guardrail_success_output(result, pydantic_obj))
    emit_metric("guardrail_reject", 1.0, guardrail="verification", reason="invalid_schema")
    return (False, "Output must be VerificationResult JSON: verified, checks_passed, checks_failed, notes")


# ---------------------------------------------------------------------------
# TaskExecutionFlow
# ---------------------------------------------------------------------------

_task_persistence: SQLiteFlowPersistence | None = None


def _get_task_persistence() -> SQLiteFlowPersistence:
    global _task_persistence
    if _task_persistence is None:
        _task_persistence = build_sqlite_flow_persistence()
    return _task_persistence


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
        checks_text = ""
        if checks_to_verify:
            checks_text = "\n\nACCEPTANCE CHECKS (verify each one):\n"
            checks_text += "\n".join(f"- {c}" for c in checks_to_verify)

        verify_agent = Agent(
            role="Independent Verifier",
            goal="Verify whether implementation artifacts exist in the codebase",
            backstory="You verify implementations by reading actual project files. "
                      "Be objective: the artifact either exists or it does not.",
            verbose=True,
            allow_delegation=False,
            reasoning=True,
            max_reasoning_attempts=2,
            llm=llm_simple,
            tools=[file_read_tool, directory_read_tool],
        )

        task_verify = Task(
            description=f"""
Verify whether task {self.state.task_id} — {self.state.task_title} was implemented.

TASK DESCRIPTION:
{self.state.task_description}

Use the file reading tool to verify whether the artifacts exist.
For each check, verify whether the file/function/config actually exists.
{checks_text}

Fill in:
- verified: true if ALL essential artifacts exist
- checks_passed: list of checks that passed
- checks_failed: list of checks that failed
- notes: explanation of what was verified
""",
            expected_output="VerificationResult",
            agent=verify_agent,
            output_pydantic=VerificationResult,
            guardrail=_verification_guardrail,
            guardrail_max_retries=2,
        )

        crew = Crew(
            agents=[verify_agent],
            tasks=[task_verify],
            verbose=True,
            memory=crew_memory(VisionContext(self.state.vision_context), "task_verify"),
            knowledge_sources=[vision_knowledge(VisionContext(self.state.vision_context))],
        )
        result = crew.kickoff()

        pydantic_result = getattr(result, "pydantic", None)
        if isinstance(pydantic_result, VerificationResult):
            return pydantic_result

        tasks_out = getattr(result, "tasks_output", None) or []
        if tasks_out:
            last_p = getattr(tasks_out[-1], "pydantic", None)
            if isinstance(last_p, VerificationResult):
                return last_p

        return VerificationResult(
            verified=False,
            notes="Failed to obtain structured VerificationResult",
        )

    @start()
    def dispatch(self):
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
        self.state.current_phase = "dialectic"
        if not self.state.phases_executed or self.state.phases_executed[-1] != "dialectic":
            self.state.phases_executed.append("dialectic")
        synthesis_for_retry: str | None = None
        vision_context = VisionContext(self.state.vision_context)
        vision_label = _vision_label(vision_context)

        for retry in range(self.state.max_retries + 1):
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
            if tasks_out and len(tasks_out) >= 1:
                impl_raw = getattr(tasks_out[0], "raw", "") or ""

            if score >= self.state.min_score:
                self.state.dialectic_score = score
                self.state.dialectic_notes = notes
                self.state.dialectic_success = True
                self.state.dialectic_retries = retry
                self.state.impl_output = impl_raw
                print(f"   {self.state.task_id} dialectic approved (score {score}/10)")
                return "passed"

            if tasks_out and len(tasks_out) >= 3:
                synthesis_for_retry = getattr(tasks_out[2], "raw", "") or ""
            else:
                synthesis_for_retry = notes

            if retry < self.state.max_retries:
                print(f"   {self.state.task_id} rejected (score {score}/10), retry {retry + 1}")

        self.state.dialectic_score = score
        self.state.dialectic_notes = notes
        self.state.dialectic_success = False
        self.state.dialectic_retries = self.state.max_retries
        print(f"   {self.state.task_id} dialectic failed ({score}/10)")
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
        self.state.current_phase = "verify"
        if not self.state.phases_executed or self.state.phases_executed[-1] != "verify":
            self.state.phases_executed.append("verify")

        vr = self._run_independent_verifier()
        self.state.verified = vr.verified
        self.state.verification = vr

        status = "PASSED" if self.state.verified else "FAILED"
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
        """Phase C: Fresh re-implementation by independent agent (no dialectic context)."""
        self.state.current_phase = "reimplement"
        if not self.state.phases_executed or self.state.phases_executed[-1] != "reimplement":
            self.state.phases_executed.append("reimplement")
        print(f"   {self.state.task_id} starting independent re-implementation (Phase C)...")
        vision_context = VisionContext(self.state.vision_context)
        vision_label = _vision_label(vision_context)

        failed_checks = self.state.verification.checks_failed
        failed_text = "\n".join(f"- {c}" for c in failed_checks) if failed_checks else "N/A"

        reimpl_agent = Agent(
            role="Independent Implementer",
            goal="Fix failed implementation based on checks that did not pass",
            backstory="You are an implementer focused on fixing specific gaps. "
                      "Read existing files, identify what is missing, and fix it.",
            verbose=True,
            allow_delegation=False,
            reasoning=True,
            max_reasoning_attempts=2,
            llm=llm_complex,
            tools=[file_read_tool, file_write_tool, directory_read_tool],
        )

        task_fix = Task(
            description=f"""
Task {self.state.task_id} — {self.state.task_title} was implemented but verification failed.

TASK DESCRIPTION:
{self.state.task_description}

FAILED CHECKS:
{failed_text}

VERIFICATION NOTES:
{self.state.verification.notes[:2000]}

Fix ONLY the identified gaps. Use the file reading and writing tools.
""",
            expected_output="Description of what was fixed",
            agent=reimpl_agent,
        )

        reval_agent = create_validador_macro(vision_context)

        task_revalidate = Task(
            description=f"""
Evaluate whether the fix for task {self.state.task_id} resolved the issues.

Consult the system's macro vision ({vision_label} is available via your knowledge sources).

Minimum score: {self.state.min_score}
Verify alignment with the macro vision.
""",
            expected_output="ValidationOutput",
            agent=reval_agent,
            output_pydantic=ValidationOutput,
            guardrail=_quality_guardrail,
            guardrail_max_retries=2,
            context=[task_fix],
        )

        crew = Crew(
            agents=[reimpl_agent, reval_agent],
            tasks=[task_fix, task_revalidate],
            process=Process.sequential,
            verbose=True,
            memory=crew_memory(vision_context, "task_reimplement"),
            knowledge_sources=[vision_knowledge(vision_context)],
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
                self.state.verified = True
                self.state.verification = VerificationResult(
                    verified=True,
                    checks_passed=failed_checks or self.state.acceptance_checks,
                    checks_failed=[],
                    notes=(
                        "High-confidence re-implementation accepted without secondary "
                        "verification pass."
                    ),
                )
                self.state.reimplement_success = True
                print(f"   {self.state.task_id} re-implementation approved ({validation.quality_score}/10)")
        else:
            score = validation.quality_score if validation else 0.0
            self.state.reimplement_score = score
            self.state.reimplement_success = False
            print(f"   {self.state.task_id} re-implementation failed ({score}/10)")
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
        self.state.current_phase = "completed"
        phases = " → ".join(self.state.phases_executed)
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
        self.state.current_phase = "failed"
        phases = " → ".join(self.state.phases_executed)
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
