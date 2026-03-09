"""
Flow principal com retry automático até quality_score >= 9.0
Implementa a dialética: Tese → Antítese → Síntese → Validação → Loop
Usa CrewAI Flow API com estado persistente

Usa features nativas do CrewAI:
- output_pydantic: structured output do Validador (PRDSchema)
- Task guardrails: validação automática do output
- Flow pattern: @start, @listen, @router para retry
"""

import json
import os
from datetime import datetime
import logging
from typing import Any

from crewai.flow import Flow, start, listen, router, or_
from crewai import Task, Crew

from dialectic.agents import visionario, critico_socratico, sintetizador, validador_macro
from dialectic.state import DialecticState, MAX_RETRIES
from dialectic.export import prd_to_markdown, PRDExporter
from dialectic.config import get_export_config
from schemas import PRDSchema

logger = logging.getLogger(__name__)

OUTPUT_DIR = "prd_output"


# ---------------------------------------------------------------------------
# Guardrail: validates PRDSchema output from Validador
# ---------------------------------------------------------------------------

def _prd_guardrail(result) -> tuple[bool, Any]:
    """Ensures validation task returns a valid PRDSchema."""
    pydantic_obj = getattr(result, "pydantic", None)
    if pydantic_obj and isinstance(pydantic_obj, PRDSchema):
        if pydantic_obj.user_stories and len(pydantic_obj.user_stories) >= 1:
            return (True, result)
        return (False, "PRD must include at least one user story")
    return (
        False,
        "Output must be a valid PRDSchema JSON. Include all required fields: "
        "feature_name, objective, macro_impact, user_stories (min 1), "
        "anti_drift_questions (min 5), quality_score, consensus_reached, "
        "final_validation_notes. Use English values for risk_level "
        "(LOW/MEDIUM/HIGH) and effort (XS/S/M/L/XL). Return ONLY the JSON.",
    )


class DialecticFlow(Flow[DialecticState]):
    """Fluxo dialético com retry automático"""

    @start()
    def iniciar_dialetica(self):
        print(f"\n{'='*60}")
        print(f"INICIANDO FLUXO DIALETICO")
        print(f"{'='*60}")
        print(f"Feature: {self.state.feature_objective}")
        print(f"Max retries: {self.state.max_retries}")
        print(f"{'='*60}\n")
        return "rodar_rodada"

    @listen(or_("iniciar_dialetica", "fazer_retry"))
    def rodar_rodada_dialetica(self):
        print(f"\nRODADA {self.state.retry_count + 1}/{self.state.max_retries}\n")

        task_vision = Task(
            description=f"""
Objetivo: {self.state.feature_objective}

VISÃO MACRO DO SISTEMA:
{self.state.vision_content}

Leia VISION.md inteiro. Gere a tese inicial completa (proposta de PRD) incluindo:
1. Nome da feature
2. Objetivo claro
3. Módulos afetados
4. User stories (mínimo 3)
5. Requisitos não-funcionais
6. Riscos identificados
7. Impacto macro
""",
            expected_output="Proposta inicial completa em formato PRD estruturado",
            agent=visionario,
        )

        task_critica = Task(
            description=f"""
Aplique método socrático completo.

Analise a proposta do Visionário (no contexto) e liste TODAS:
1. Falhas e pontos fracos
2. Contradições com VISION.md
3. Riscos de drift
4. Overscope e dívida técnica
5. Requisitos não-funcionais esquecidos
6. User stories fracas ou incompletas

Seja implacável. Cada crítica deve ser específica e acionável.
""",
            expected_output="Crítica detalhada com lista de problemas e nota",
            agent=critico_socratico,
            context=[task_vision],
        )

        task_sintese = Task(
            description=f"""
Produza a síntese final incorporando TODAS as críticas (tese e antítese estão no contexto).

A síntese deve:
1. Preservar o que havia de bom na tese
2. Incorporar TODAS as críticas da antítese
3. Eliminar TODAS as fraquezas identificadas
4. Ser melhor que ambas as propostas individuais
5. Estar alinhada com VISION.md

Output: PRD completo com user stories corrigidas, em formato estruturado (objetivo, macro_impact, user_stories, anti_drift_questions). Use risk_level em inglês (LOW/MEDIUM/HIGH) e effort em inglês (XS/S/M/L/XL) para compatibilidade com o schema.
""",
            expected_output="Versão final refinada do PRD",
            agent=sintetizador,
            context=[task_vision, task_critica],
        )

        task_validacao = Task(
            description=f"""
Avalie a SÍNTESE FINAL (output do Sintetizador no contexto) e produza o PRD final.

O PRD deve seguir exatamente a estrutura do PRDSchema:
- feature_name, version, objective
- macro_impact: {{ modules_affected, risk_level, performance_impact, security_impact }}
- user_stories: [ {{ id, title, description, acceptance_criteria, effort, dependencies }} ]
- anti_drift_questions: [ {{ question, answer }} ]
- quality_score: float (uma casa decimal, 0-10)
- consensus_reached: true ou false
- final_validation_notes: string

Use o conteúdo da síntese para preencher os campos. Se score < 9.0, explique em final_validation_notes o que falta.

Checklist para score: (1) Feature alinhada com visão macro? (2) Módulos afetados? (3) Riscos mitigados? (4) NFRs cobertos? (5) User stories consistentes? (6) 5+ anti-drift?

OBRIGATÓRIO - use EXATAMENTE estes valores em inglês (nunca em português):
- risk_level: apenas "LOW", "MEDIUM" ou "HIGH"
- effort: apenas "XS", "S", "M", "L" ou "XL"
""",
            expected_output="PRDSchema válido com quality_score e consensus_reached",
            agent=validador_macro,
            output_pydantic=PRDSchema,
            guardrail=_prd_guardrail,
            guardrail_max_retries=2,
            context=[task_vision, task_critica, task_sintese],
        )

        crew = Crew(
            agents=[visionario, critico_socratico, sintetizador, validador_macro],
            tasks=[task_vision, task_critica, task_sintese, task_validacao],
            process="sequential",
            verbose=True,
        )

        resultado = crew.kickoff(
            inputs={
                "feature_objective": self.state.feature_objective,
                "vision_content": self.state.vision_content,
            }
        )

        # Extract PRD via output_pydantic (native CrewAI structured output)
        prd: PRDSchema | None = None
        pydantic_result = getattr(resultado, "pydantic", None)
        if isinstance(pydantic_result, PRDSchema):
            prd = pydantic_result
        else:
            tasks_out = getattr(resultado, "tasks_output", None) or []
            if tasks_out:
                last_pydantic = getattr(tasks_out[-1], "pydantic", None)
                if isinstance(last_pydantic, PRDSchema):
                    prd = last_pydantic

        if prd is not None:
            self.state.prd_data = prd.model_dump()
            self.state.quality_score = prd.quality_score
            self.state.consensus_reached = prd.consensus_reached
            self.state.final_validation_notes = prd.final_validation_notes
        else:
            # Fallback: parse raw text (should rarely trigger with output_pydantic)
            raw_text = getattr(resultado, "raw", None) or str(resultado)
            tasks_out = getattr(resultado, "tasks_output", None) or []
            if tasks_out:
                last_raw = getattr(tasks_out[-1], "raw", None)
                if last_raw and isinstance(last_raw, str) and last_raw.strip():
                    raw_text = last_raw
            try:
                import re
                match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw_text)
                json_str = match.group(1).strip() if match else raw_text
                start_idx = json_str.find("{")
                if start_idx >= 0:
                    json_str = json_str[start_idx:]
                prd_dict = json.loads(json_str)
                prd = PRDSchema.model_validate(prd_dict)
                self.state.prd_data = prd.model_dump()
                self.state.quality_score = prd.quality_score
                self.state.consensus_reached = prd.consensus_reached
                self.state.final_validation_notes = prd.final_validation_notes
            except Exception:
                self.state.prd_data = {"raw": raw_text[:5000]}
                self.state.quality_score = 5.0
                self.state.consensus_reached = False
                self.state.final_validation_notes = "Falha ao extrair PRD (output_pydantic e parsing falharam)."
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                debug_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_path = os.path.join(OUTPUT_DIR, f"debug_crew_output_{debug_ts}.txt")
                try:
                    with open(debug_path, "w", encoding="utf-8") as f:
                        f.write("# Raw crew output (parse failed)\n\n")
                        f.write(raw_text if isinstance(raw_text, str) else str(raw_text))
                    print(f"   Debug: raw output salvo em {debug_path}")
                except OSError:
                    pass

        print(f"\n{'='*60}")
        print(f"QUALITY SCORE: {self.state.quality_score}/10.0")
        print(f"{'='*60}")
        return "avaliar"

    @router(rodar_rodada_dialetica)
    def avaliar(self):
        if self.state.quality_score >= 9.0:
            print(f"APROVADO! Quality score: {self.state.quality_score}")
            return "aprovar"
        elif self.state.retry_count >= self.state.max_retries:
            print(f"Max retries atingido. Finalizando com score: {self.state.quality_score}")
            return "aprovar"
        else:
            self.state.retry_count += 1
            print(f"Reprovado. Retry #{self.state.retry_count}")
            notes = self.state.final_validation_notes
            notes_str = notes[:200] if isinstance(notes, str) else str(notes)[:200]
            print(f"   O que falta: {notes_str}...")
            return "retry"

    @listen("retry")
    def fazer_retry(self):
        return "rodar_rodada"

    @listen("aprovar")
    def salvar_prd_final(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Build PRD from state data
        data = self.state.prd_data if isinstance(self.state.prd_data, dict) else {}
        try:
            prd = PRDSchema.model_validate(data)
        except Exception:
            prd = PRDSchema(
                feature_name=data.get("feature_name") or self.state.feature_objective,
                version=data.get("version") or "1.0",
                objective=data.get("objective") or self.state.feature_objective,
                macro_impact=data.get("macro_impact") or {
                    "modules_affected": ["N/A"],
                    "risk_level": "MEDIUM",
                    "performance_impact": "N/A",
                    "security_impact": "N/A",
                },
                user_stories=data.get("user_stories") or [
                    {"id": "US-001", "title": "Placeholder", "description": "N/A",
                     "acceptance_criteria": ["N/A", "N/A", "N/A"], "effort": "M"}
                ],
                anti_drift_questions=data.get("anti_drift_questions") or [
                    {"question": "N/A", "answer": "N/A"} for _ in range(5)
                ],
                quality_score=float(self.state.quality_score),
                consensus_reached=bool(self.state.consensus_reached),
                final_validation_notes=str(self.state.final_validation_notes or ""),
            )

        prd.quality_score = self.state.quality_score
        prd.consensus_reached = self.state.consensus_reached
        prd.final_validation_notes = self.state.final_validation_notes

        if float(self.state.quality_score) >= 9.0:
            try:
                config = get_export_config()
                exporter = PRDExporter()
                created_paths = exporter.export(prd, config)
                logger.info("PRD exported via PRDExporter: %s", created_paths)
                print(f"\nPRD APROVADO com nota {self.state.quality_score}!")
                for p in created_paths:
                    print(f"Salvo em: {p}")
                return prd
            except Exception as e:
                logger.exception("Failed to export PRD via PRDExporter: %s", e)
                print("Falha ao exportar PRD via PRDExporter; caindo para salvamento local.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{OUTPUT_DIR}/PRD_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(prd.model_dump(), f, indent=2, ensure_ascii=False)

        filename_md = filename.replace(".json", ".md")
        with open(filename_md, "w", encoding="utf-8") as f:
            f.write(prd_to_markdown(prd))

        print(f"\nPRD APROVADO com nota {self.state.quality_score}!")
        print(f"Salvo em: {filename}")
        print(f"Markdown: {filename_md}")
        return prd


def run_dialectic_flow(feature_request: str, vision_content: str) -> dict:
    state = DialecticState(
        feature_objective=feature_request,
        vision_content=vision_content,
        max_retries=MAX_RETRIES,
    )
    flow = DialecticFlow(state)
    result = flow.kickoff()
    return {
        "success": result.consensus_reached or result.quality_score >= 9.0,
        "quality_score": result.quality_score,
        "iterations": result.retry_count + 1,
        "prd": result.prd_data,
        "consensus_reached": result.consensus_reached,
        "validation": result.final_validation_notes,
    }
