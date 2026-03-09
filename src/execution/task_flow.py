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
from typing import Any

from crewai import Task, Crew, Agent
from crewai.flow.flow import Flow, start, listen, router
from pydantic import BaseModel, Field

from dialectic.agents import (
    implementer,
    validador_macro,
    critico_socratico,
    sintetizador,
)
from dialectic.tools import file_read_tool, file_write_tool
from schemas import (
    ValidationOutput,
    VerificationResult,
    TaskExecutionResult,
)

CREW_KICKOFF_TIMEOUT = int(os.getenv("CREW_KICKOFF_TIMEOUT", "300"))
DEFAULT_MIN_SCORE = float(os.getenv("MIN_QUALITY_SCORE", "7.5"))
DEFAULT_MAX_RETRIES = int(os.getenv("MAX_RETRIES_PER_TASK", "3"))


class TaskFlowState(BaseModel):
    task_id: str = ""
    task_title: str = ""
    task_description: str = ""
    context_str: str = ""
    vision_content: str = ""
    acceptance_checks: list[str] = Field(default_factory=list)
    min_score: float = DEFAULT_MIN_SCORE
    max_retries: int = DEFAULT_MAX_RETRIES

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


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------

def _quality_guardrail(result) -> tuple[bool, Any]:
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, ValidationOutput):
        if 0.0 <= pydantic_obj.quality_score <= 10.0:
            return (True, result)
        return (False, "quality_score must be between 0.0 and 10.0")
    return (False, "Output must be valid JSON: quality_score, consensus_reached, final_validation_notes")


def _verification_guardrail(result) -> tuple[bool, Any]:
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, VerificationResult):
        return (True, result)
    return (False, "Output must be VerificationResult JSON: verified, checks_passed, checks_failed, notes")


# ---------------------------------------------------------------------------
# TaskExecutionFlow
# ---------------------------------------------------------------------------

class TaskExecutionFlow(Flow[TaskFlowState]):
    """
    Per-task execution with three phases:
    1. Dialectic cycle (implement → critique → synthesize → validate)
    2. Post-execution verification (A) with acceptance criteria (B)
    3. Independent re-implementation (C) if verification fails
    """

    @start()
    def run_dialectic(self):
        """Phase 0: Full dialectic cycle with retries."""
        self.state.phases_executed.append("dialectic")
        synthesis_for_retry: str | None = None

        for retry in range(self.state.max_retries + 1):
            if synthesis_for_retry is None:
                tese_input = f"""
TASK TO IMPLEMENT: {self.state.task_id} — {self.state.task_title}

{self.state.task_description}

CONTEXT:
{self.state.context_str}

VISION.md (read before implementing):
{self.state.vision_content[:4000]}
"""
            else:
                tese_input = f"""
RETRY {retry}/{self.state.max_retries} — Incorporate ALL refinements below.

TASK: {self.state.task_id} — {self.state.task_title}

CRITIQUES AND REFINEMENTS:
{synthesis_for_retry[:3000]}

Re-implement incorporating these refinements.
"""

            task_impl = Task(
                description=tese_input,
                expected_output="Description of what was implemented and files created/modified",
                agent=implementer,
            )
            task_critica = Task(
                description=f"""
Analyze the implementation of task {self.state.task_id} — {self.state.task_title}.
SCOPE: Evaluate ONLY whether it meets the description: \"\"\"{self.state.task_description}\"\"\"
Do NOT critique outside the scope. Do NOT request additional features.
""",
                expected_output="Detailed critique of the implementation",
                agent=critico_socratico,
                context=[task_impl],
            )
            task_sintese = Task(
                description=f"""
Produce the SYNTHESIS for task {self.state.task_id}: incorporate ALL critiques.
Include clear instructions for retry if necessary.
""",
                expected_output="Refined synthesis with instructions",
                agent=sintetizador,
                context=[task_impl, task_critica],
            )
            task_val = Task(
                description=f"""
Evaluate the implementation of task {self.state.task_id}.
Minimum score for approval: {self.state.min_score}
""",
                expected_output="ValidationOutput",
                agent=validador_macro,
                output_pydantic=ValidationOutput,
                guardrail=_quality_guardrail,
                guardrail_max_retries=2,
                context=[task_impl, task_critica, task_sintese],
            )

            crew = Crew(
                agents=[implementer, critico_socratico, sintetizador, validador_macro],
                tasks=[task_impl, task_critica, task_sintese, task_val],
                process="sequential",
                verbose=True,
            )

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
            return "verify"
        return "mark_failed"

    @listen("verify")
    def verify_implementation(self):
        """Phase A: Verify artifacts + Phase B: Check acceptance criteria."""
        self.state.phases_executed.append("verify")

        checks_text = ""
        if self.state.acceptance_checks:
            checks_text = "\n\nACCEPTANCE CHECKS (verify each one):\n"
            checks_text += "\n".join(f"- {c}" for c in self.state.acceptance_checks)

        verify_agent = Agent(
            role="Independent Verifier",
            goal="Verify whether implementation artifacts exist in the codebase",
            backstory="You verify implementations by reading actual project files. "
                      "Be objective: the artifact either exists or it does not.",
            verbose=True,
            allow_delegation=False,
            reasoning=True,
            max_reasoning_attempts=2,
            llm=validador_macro.llm,
            tools=[file_read_tool],
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

        crew = Crew(agents=[verify_agent], tasks=[task_verify], verbose=True)
        result = crew.kickoff()

        vr: VerificationResult | None = None
        pydantic_result = getattr(result, "pydantic", None)
        if isinstance(pydantic_result, VerificationResult):
            vr = pydantic_result
        else:
            tasks_out = getattr(result, "tasks_output", None) or []
            if tasks_out:
                last_p = getattr(tasks_out[-1], "pydantic", None)
                if isinstance(last_p, VerificationResult):
                    vr = last_p

        if vr:
            self.state.verified = vr.verified
            self.state.verification = vr
        else:
            self.state.verified = False
            self.state.verification = VerificationResult(
                verified=False, notes="Failed to obtain structured VerificationResult"
            )

        status = "PASSED" if self.state.verified else "FAILED"
        print(f"   {self.state.task_id} verification: {status}")
        if self.state.verification.checks_failed:
            print(f"      Failed checks: {self.state.verification.checks_failed}")
        return "done"

    @router(verify_implementation)
    def evaluate_verification(self):
        if self.state.verified:
            return "mark_completed"
        return "reimplement"

    @listen("reimplement")
    def independent_reimplement(self):
        """Phase C: Fresh re-implementation by independent agent (no dialectic context)."""
        self.state.phases_executed.append("reimplement")
        print(f"   {self.state.task_id} starting independent re-implementation (Phase C)...")

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
            llm=implementer.llm,
            tools=[file_read_tool, file_write_tool],
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

        task_revalidate = Task(
            description=f"""
Evaluate whether the fix for task {self.state.task_id} resolved the issues.
Minimum score: {self.state.min_score}
""",
            expected_output="ValidationOutput",
            agent=validador_macro,
            output_pydantic=ValidationOutput,
            guardrail=_quality_guardrail,
            guardrail_max_retries=2,
            context=[task_fix],
        )

        crew = Crew(
            agents=[reimpl_agent, validador_macro],
            tasks=[task_fix, task_revalidate],
            process="sequential",
            verbose=True,
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
            self.state.reimplement_success = True
            impl_raw = getattr(tasks_out[0], "raw", "") if tasks_out else ""
            self.state.reimplement_output = impl_raw
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
            return "mark_completed"
        return "mark_failed"

    @listen("mark_completed")
    def on_completed(self):
        phases = " → ".join(self.state.phases_executed)
        print(f"   {self.state.task_id} COMPLETED (phases: {phases})")
        return self._build_result(success=True)

    @listen("mark_failed")
    def on_failed(self):
        phases = " → ".join(self.state.phases_executed)
        print(f"   {self.state.task_id} FAILED (phases: {phases})")
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
            validation_notes=notes[:1000],
            output_summary=best_output[:5000],
            verification=self.state.verification if self.state.verified or self.state.verification.notes else None,
            execution_phases=self.state.phases_executed,
        )
