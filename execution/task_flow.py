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
TASK A IMPLEMENTAR: {self.state.task_id} — {self.state.task_title}

{self.state.task_description}

CONTEXTO:
{self.state.context_str}

VISION.md (leia antes de implementar):
{self.state.vision_content[:4000]}
"""
            else:
                tese_input = f"""
RETRY {retry}/{self.state.max_retries} — Incorpore TODOS os refinamentos abaixo.

TASK: {self.state.task_id} — {self.state.task_title}

CRÍTICAS E REFINAMENTOS:
{synthesis_for_retry[:3000]}

Implemente novamente incorporando esses refinamentos.
"""

            task_impl = Task(
                description=tese_input,
                expected_output="Descrição do que foi implementado e arquivos criados/modificados",
                agent=implementer,
            )
            task_critica = Task(
                description=f"""
Analise a implementação da task {self.state.task_id} — {self.state.task_title}.
ESCOPO: Avalie SOMENTE se atende à descrição: \"\"\"{self.state.task_description}\"\"\"
NÃO critique fora do escopo. NÃO peça features adicionais.
""",
                expected_output="Crítica detalhada da implementação",
                agent=critico_socratico,
                context=[task_impl],
            )
            task_sintese = Task(
                description=f"""
Produza a SÍNTESE para a task {self.state.task_id}: incorpore TODAS as críticas.
Inclua instruções claras para retry se necessário.
""",
                expected_output="Síntese refinada com instruções",
                agent=sintetizador,
                context=[task_impl, task_critica],
            )
            task_val = Task(
                description=f"""
Avalie a implementação da task {self.state.task_id}.
Score mínimo para aprovação: {self.state.min_score}
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
                print(f"   {self.state.task_id} dialética aprovada (score {score}/10)")
                return "passed"

            if tasks_out and len(tasks_out) >= 3:
                synthesis_for_retry = getattr(tasks_out[2], "raw", "") or ""
            else:
                synthesis_for_retry = notes

            if retry < self.state.max_retries:
                print(f"   {self.state.task_id} reprovada (score {score}/10), retry {retry + 1}")

        self.state.dialectic_score = score
        self.state.dialectic_notes = notes
        self.state.dialectic_success = False
        self.state.dialectic_retries = self.state.max_retries
        print(f"   {self.state.task_id} dialética falhou ({score}/10)")
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
            checks_text = "\n\nACCEPTANCE CHECKS (verifique cada um):\n"
            checks_text += "\n".join(f"- {c}" for c in self.state.acceptance_checks)

        verify_agent = Agent(
            role="Verificador Independente",
            goal="Verificar se artefatos de implementação existem no codebase",
            backstory="Você verifica implementações lendo arquivos reais do projeto. "
                      "Seja objetivo: o artefato existe ou não existe.",
            verbose=True,
            allow_delegation=False,
            reasoning=True,
            max_reasoning_attempts=2,
            llm=validador_macro.llm,
            tools=[file_read_tool],
        )

        task_verify = Task(
            description=f"""
Verifique se a task {self.state.task_id} — {self.state.task_title} foi implementada.

DESCRIÇÃO DA TASK:
{self.state.task_description}

Use a ferramenta de leitura de arquivo para verificar se os artefatos existem.
Para cada check, verifique se o arquivo/função/config realmente existe.
{checks_text}

Preencha:
- verified: true se TODOS os artefatos essenciais existem
- checks_passed: lista de checks que passaram
- checks_failed: lista de checks que falharam
- notes: explicação do que foi verificado
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
                verified=False, notes="Falha ao obter VerificationResult estruturado"
            )

        status = "PASSED" if self.state.verified else "FAILED"
        print(f"   {self.state.task_id} verificação: {status}")
        if self.state.verification.checks_failed:
            print(f"      Checks falharam: {self.state.verification.checks_failed}")
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
        print(f"   {self.state.task_id} iniciando re-implementação independente (Phase C)...")

        failed_checks = self.state.verification.checks_failed
        failed_text = "\n".join(f"- {c}" for c in failed_checks) if failed_checks else "N/A"

        reimpl_agent = Agent(
            role="Implementador Independente",
            goal="Corrigir implementação falhada baseado nos checks que não passaram",
            backstory="Você é um implementador focado em corrigir gaps específicos. "
                      "Leia os arquivos existentes, identifique o que falta, e corrija.",
            verbose=True,
            allow_delegation=False,
            reasoning=True,
            max_reasoning_attempts=2,
            llm=implementer.llm,
            tools=[file_read_tool, file_write_tool],
        )

        task_fix = Task(
            description=f"""
A task {self.state.task_id} — {self.state.task_title} foi implementada mas a verificação falhou.

DESCRIÇÃO DA TASK:
{self.state.task_description}

CHECKS QUE FALHARAM:
{failed_text}

NOTAS DA VERIFICAÇÃO:
{self.state.verification.notes[:2000]}

Corrija APENAS os gaps identificados. Use as ferramentas de leitura e escrita de arquivos.
""",
            expected_output="Descrição do que foi corrigido",
            agent=reimpl_agent,
        )

        task_revalidate = Task(
            description=f"""
Avalie se a correção da task {self.state.task_id} resolveu os problemas.
Score mínimo: {self.state.min_score}
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
            print(f"   {self.state.task_id} re-implementação aprovada ({validation.quality_score}/10)")
        else:
            score = validation.quality_score if validation else 0.0
            self.state.reimplement_score = score
            self.state.reimplement_success = False
            print(f"   {self.state.task_id} re-implementação falhou ({score}/10)")
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
            notes += f" | Verificação: {self.state.verification.notes[:300]}"

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
